# llm_quality_assessment.py

import os
import json
import time
import hashlib
import statistics
import re
from datetime import datetime
from typing import Dict, List, Tuple, Any
from collections import defaultdict
import numpy as np
import pandas as pd
from dataclasses import dataclass, asdict
import tiktoken
import pymysql
from dotenv import load_dotenv

@dataclass
class TrialInput:
    """Standard input for assessment trials"""
    use_case: str
    sector: str
    demand: str
    trial_id: str = None
    
    def __post_init__(self):
        if not self.trial_id:
            self.trial_id = hashlib.md5(
                f"{self.use_case}:{self.sector}:{self.demand}:{datetime.now().isoformat()}".encode()
            ).hexdigest()[:8]

@dataclass
class TrialResult:
    """Result from a single trial run"""
    trial_id: str
    timestamp: datetime
    input: TrialInput
    
    # Output data
    raw_output: str
    trend_titles: List[str]
    trend_blocks: List[str]
    
    # Performance metrics
    latency_ms: float
    token_count: int
    api_calls: int
    
    # Extracted data
    confidence_scores: List[float]
    budgets: List[Dict[str, float]]
    timelines: List[Dict[str, str]]
    
    # Quality flags
    structure_compliance: Dict[str, bool]
    parsing_errors: List[str]

class LLMQualityAssessor:
    """Main assessment engine for LLM output quality"""
    
    def __init__(self, config_path=".env"):
        load_dotenv(config_path)
        self.encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
        self.trial_results = []
        self.setup_database()
        
    def setup_database(self):
        """Create assessment tables if not exist"""
        try:
            conn = pymysql.connect(
                host=os.getenv("DB_HOST"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                database=os.getenv("DB_NAME"),
                charset="utf8mb4"
            )
            
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS llm_assessment_trials (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    trial_id VARCHAR(32) UNIQUE,
                    use_case VARCHAR(255),
                    sector VARCHAR(255),
                    demand TEXT,
                    timestamp DATETIME,
                    raw_output LONGTEXT,
                    latency_ms FLOAT,
                    token_count INT,
                    api_calls INT,
                    metadata JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_input (use_case, sector, demand(255))
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS llm_assessment_metrics (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    assessment_id VARCHAR(32),
                    metric_type VARCHAR(50),
                    metric_name VARCHAR(100),
                    metric_value FLOAT,
                    details JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_assessment (assessment_id),
                    INDEX idx_metric (metric_type, metric_name)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Database setup error: {e}")
    
    def run_trial(self, trial_input: TrialInput, app_function) -> TrialResult:
        """Run a single trial and collect metrics"""
        
        start_time = time.time()
        api_call_count = 0
        
        # Mock or instrument the LLM call counter
        original_call_llm = app_function.__globals__.get('call_llm')
        
        def instrumented_call_llm(*args, **kwargs):
            nonlocal api_call_count
            api_call_count += 1
            return original_call_llm(*args, **kwargs)
        
        # Temporarily replace
        app_function.__globals__['call_llm'] = instrumented_call_llm
        
        try:
            # Run the actual function
            raw_output = app_function(
                trial_input.use_case,
                trial_input.sector,
                trial_input.demand
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Parse output
            parsed = self.parse_output(raw_output)
            
            # Count tokens
            token_count = len(self.encoding.encode(raw_output))
            
            # Create result
            result = TrialResult(
                trial_id=trial_input.trial_id,
                timestamp=datetime.now(),
                input=trial_input,
                raw_output=raw_output,
                trend_titles=parsed['titles'],
                trend_blocks=parsed['blocks'],
                latency_ms=latency_ms,
                token_count=token_count,
                api_calls=api_call_count,
                confidence_scores=parsed['confidence_scores'],
                budgets=parsed['budgets'],
                timelines=parsed['timelines'],
                structure_compliance=parsed['compliance'],
                parsing_errors=parsed['errors']
            )
            
            # Store result
            self.store_trial_result(result)
            self.trial_results.append(result)
            
            return result
            
        finally:
            # Restore original function
            app_function.__globals__['call_llm'] = original_call_llm
    
    def parse_output(self, raw_output: str) -> Dict[str, Any]:
        """Parse LLM output and extract structured data"""
        
        result = {
            'titles': [],
            'blocks': [],
            'confidence_scores': [],
            'budgets': [],
            'timelines': [],
            'compliance': {},
            'errors': []
        }
        
        try:
            # Extract trend titles
            title_pattern = r"Technology Title:\s*(.+)"
            titles = re.findall(title_pattern, raw_output, re.IGNORECASE)
            result['titles'] = titles
            
            # Split into blocks
            blocks = re.split(r"---+", raw_output)
            result['blocks'] = [b.strip() for b in blocks if b.strip()]
            
            # Extract confidence scores
            confidence_pattern = r"Confidence Score:\s*([0-9.]+)"
            scores = re.findall(confidence_pattern, raw_output, re.IGNORECASE)
            result['confidence_scores'] = [float(s) for s in scores]
            
            # Extract budgets (various formats)
            budget_patterns = [
                r"€\s*([0-9.]+)\s*[MBmb]illion",
                r"Budget:\s*€\s*([0-9.]+)\s*million",
                r"Investment.*?€\s*([0-9.]+)-([0-9.]+)\s*million"
            ]
            
            for pattern in budget_patterns:
                matches = re.findall(pattern, raw_output, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        result['budgets'].append({
                            'min': float(match[0]),
                            'max': float(match[1]) if len(match) > 1 else float(match[0])
                        })
                    else:
                        result['budgets'].append({'value': float(match)})
            
            # Extract timelines
            timeline_pattern = r"(\d+)\s*mo(?:nths?)?\s*[-–]\s*([^,\n]+)"
            timelines = re.findall(timeline_pattern, raw_output)
            result['timelines'] = [
                {'months': int(t[0]), 'milestone': t[1].strip()} 
                for t in timelines
            ]
            
            # Check structure compliance
            required_sections = [
                'Strategic Alignment',
                'Confidence Justification',
                'Market Impact',
                'Value Proposition',
                'Competitive Landscape',
                'Implementation Readiness'
            ]
            
            for section in required_sections:
                result['compliance'][section] = bool(
                    re.search(rf"\*\*{section}", raw_output, re.IGNORECASE)
                )
            
            # Check for tables
            result['compliance']['has_tables'] = '|' in raw_output and '---' in raw_output
            
        except Exception as e:
            result['errors'].append(f"Parsing error: {str(e)}")
        
        return result
    
    def calculate_diversity_metrics(self, results: List[TrialResult]) -> Dict[str, float]:
        """Calculate diversity metrics across multiple trials"""
        
        metrics = {}
        
        if not results:
            return metrics
        
        # Title diversity (Jaccard similarity)
        all_titles = [title for r in results for title in r.trend_titles]
        unique_titles = set(all_titles)
        
        if len(results) > 1:
            # Average pairwise Jaccard similarity
            similarities = []
            for i in range(len(results)):
                for j in range(i + 1, len(results)):
                    set1 = set(results[i].trend_titles)
                    set2 = set(results[j].trend_titles)
                    if set1 or set2:
                        jaccard = len(set1 & set2) / len(set1 | set2)
                        similarities.append(jaccard)
            
            metrics['title_diversity'] = 1 - np.mean(similarities) if similarities else 1.0
        else:
            metrics['title_diversity'] = 1.0
        
        metrics['unique_title_ratio'] = len(unique_titles) / len(all_titles) if all_titles else 0
        
        # Semantic diversity (simplified - could use embeddings)
        metrics['avg_titles_per_trial'] = np.mean([len(r.trend_titles) for r in results])
        metrics['title_count_std'] = np.std([len(r.trend_titles) for r in results])
        
        return metrics
    
    def calculate_stability_metrics(self, results: List[TrialResult]) -> Dict[str, float]:
        """Calculate stability metrics for numeric fields"""
        
        metrics = {}
        
        if not results:
            return metrics
        
        # Confidence score stability (Coefficient of Variation)
        all_scores = [score for r in results for score in r.confidence_scores]
        if all_scores:
            mean_score = np.mean(all_scores)
            std_score = np.std(all_scores)
            metrics['confidence_cv'] = (std_score / mean_score) if mean_score > 0 else 0
            metrics['confidence_mean'] = mean_score
            metrics['confidence_std'] = std_score
        
        # Budget stability
        all_budgets = []
        for r in results:
            for budget in r.budgets:
                if 'value' in budget:
                    all_budgets.append(budget['value'])
                elif 'min' in budget and 'max' in budget:
                    all_budgets.append((budget['min'] + budget['max']) / 2)
        
        if all_budgets:
            mean_budget = np.mean(all_budgets)
            std_budget = np.std(all_budgets)
            metrics['budget_cv'] = (std_budget / mean_budget) if mean_budget > 0 else 0
            metrics['budget_mean'] = mean_budget
            metrics['budget_std'] = std_budget
        
        # Timeline consistency
        timeline_months = []
        for r in results:
            for timeline in r.timelines:
                timeline_months.append(timeline['months'])
        
        if timeline_months:
            metrics['timeline_consistency'] = len(set(timeline_months)) / len(timeline_months)
        
        return metrics
    
    def calculate_compliance_metrics(self, results: List[TrialResult]) -> Dict[str, float]:
        """Calculate structure compliance metrics"""
        
        metrics = {}
        
        if not results:
            return metrics
        
        # Overall compliance rate
        compliance_scores = []
        for r in results:
            if r.structure_compliance:
                score = sum(r.structure_compliance.values()) / len(r.structure_compliance)
                compliance_scores.append(score)
        
        metrics['avg_compliance'] = np.mean(compliance_scores) if compliance_scores else 0
        
        # Section-specific compliance
        section_compliance = defaultdict(list)
        for r in results:
            for section, compliant in r.structure_compliance.items():
                section_compliance[section].append(1 if compliant else 0)
        
        for section, values in section_compliance.items():
            metrics[f'compliance_{section.lower().replace(" ", "_")}'] = np.mean(values)
        
        # Error rate
        error_count = sum(len(r.parsing_errors) for r in results)
        metrics['error_rate'] = error_count / len(results) if results else 0
        
        return metrics
    
    def calculate_performance_metrics(self, results: List[TrialResult]) -> Dict[str, float]:
        """Calculate operational performance metrics"""
        
        metrics = {}
        
        if not results:
            return metrics
        
        # Latency statistics
        latencies = [r.latency_ms for r in results]
        metrics['latency_mean'] = np.mean(latencies)
        metrics['latency_std'] = np.std(latencies)
        metrics['latency_p50'] = np.percentile(latencies, 50)
        metrics['latency_p95'] = np.percentile(latencies, 95)
        
        # Token usage
        tokens = [r.token_count for r in results]
        metrics['tokens_mean'] = np.mean(tokens)
        metrics['tokens_std'] = np.std(tokens)
        metrics['tokens_total'] = sum(tokens)
        
        # API efficiency
        api_calls = [r.api_calls for r in results]
        metrics['api_calls_mean'] = np.mean(api_calls)
        metrics['api_calls_total'] = sum(api_calls)
        
        # Cost estimation (rough)
        # GPT-3.5: ~$0.002 per 1K tokens
        metrics['estimated_cost_usd'] = (metrics['tokens_total'] / 1000) * 0.002
        
        return metrics
    
    def run_assessment_suite(
        self, 
        trial_input: TrialInput, 
        num_trials: int,
        app_function
    ) -> Dict[str, Any]:
        """Run complete assessment suite"""
        
        print(f"Running {num_trials} trials for: {trial_input.use_case} / {trial_input.sector} / {trial_input.demand}")
        
        assessment_id = hashlib.md5(
            f"{trial_input.use_case}:{trial_input.sector}:{trial_input.demand}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]
        
        # Run trials
        results = []
        for i in range(num_trials):
            print(f"Trial {i+1}/{num_trials}...", end='', flush=True)
            
            trial_input.trial_id = f"{assessment_id}_{i+1}"
            result = self.run_trial(trial_input, app_function)
            results.append(result)
            
            print(f" ✓ ({result.latency_ms:.0f}ms)")
            
            # Small delay to avoid rate limiting
            if i < num_trials - 1:
                time.sleep(2)
        
        # Calculate all metrics
        assessment = {
            'assessment_id': assessment_id,
            'input': asdict(trial_input),
            'num_trials': num_trials,
            'timestamp': datetime.now().isoformat(),
            'metrics': {
                'diversity': self.calculate_diversity_metrics(results),
                'stability': self.calculate_stability_metrics(results),
                'compliance': self.calculate_compliance_metrics(results),
                'performance': self.calculate_performance_metrics(results)
            },
            'trial_ids': [r.trial_id for r in results]
        }
        
        # Store assessment
        self.store_assessment(assessment)
        
        return assessment
    
    def store_trial_result(self, result: TrialResult):
        """Store individual trial result in database"""
        try:
            conn = pymysql.connect(
                host=os.getenv("DB_HOST"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                database=os.getenv("DB_NAME"),
                charset="utf8mb4"
            )
            
            cursor = conn.cursor()
            
            metadata = {
                'trend_count': len(result.trend_titles),
                'confidence_scores': result.confidence_scores,
                'structure_compliance': result.structure_compliance,
                'errors': result.parsing_errors
            }
            
            cursor.execute("""
                INSERT INTO llm_assessment_trials 
                (trial_id, use_case, sector, demand, timestamp, 
                 raw_output, latency_ms, token_count, api_calls, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                result.trial_id,
                result.input.use_case,
                result.input.sector,
                result.input.demand,
                result.timestamp,
                result.raw_output,
                result.latency_ms,
                result.token_count,
                result.api_calls,
                json.dumps(metadata)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Error storing trial result: {e}")
    
    def store_assessment(self, assessment: Dict[str, Any]):
        """Store assessment metrics in database"""
        try:
            conn = pymysql.connect(
                host=os.getenv("DB_HOST"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                database=os.getenv("DB_NAME"),
                charset="utf8mb4"
            )
            
            cursor = conn.cursor()
            
            # Store each metric
            for metric_type, metrics in assessment['metrics'].items():
                for metric_name, metric_value in metrics.items():
                    cursor.execute("""
                        INSERT INTO llm_assessment_metrics
                        (assessment_id, metric_type, metric_name, metric_value, details)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (
                        assessment['assessment_id'],
                        metric_type,
                        metric_name,
                        float(metric_value) if isinstance(metric_value, (int, float)) else 0,
                        json.dumps({'raw_value': metric_value})
                    ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Error storing assessment: {e}")
    
    def generate_report(self, assessment: Dict[str, Any]) -> str:
        """Generate human-readable assessment report"""
        
        report = f"""
# LLM Output Quality Assessment Report
Generated: {assessment['timestamp']}

## Assessment Details
- **Use Case**: {assessment['input']['use_case']}
- **Sector**: {assessment['input']['sector']}
- **Demand**: {assessment['input']['demand']}
- **Number of Trials**: {assessment['num_trials']}
- **Assessment ID**: {assessment['assessment_id']}

## Executive Summary

### 🎯 Key Findings
"""
        
        # Diversity score
        diversity = assessment['metrics']['diversity']
        if diversity.get('title_diversity', 0) > 0.7:
            report += "- ✅ **High output diversity**: Different trends generated across trials\n"
        else:
            report += "- ⚠️ **Low output diversity**: Similar trends repeated across trials\n"
        
        # Stability score
        stability = assessment['metrics']['stability']
        if stability.get('confidence_cv', 1) < 0.15:
            report += "- ✅ **Stable numeric outputs**: Consistent confidence scores and budgets\n"
        else:
            report += "- ⚠️ **Variable numeric outputs**: Large variations in scores and budgets\n"
        
        # Compliance score
        compliance = assessment['metrics']['compliance']
        if compliance.get('avg_compliance', 0) > 0.9:
            report += "- ✅ **Excellent structure compliance**: All required sections present\n"
        else:
            report += "- ⚠️ **Structure compliance issues**: Some required sections missing\n"
        
        # Performance
        performance = assessment['metrics']['performance']
        if performance.get('latency_p95', 0) < 30000:  # 30 seconds
            report += "- ✅ **Good performance**: Acceptable response times\n"
        else:
            report += "- ⚠️ **Performance concerns**: High response times observed\n"
        
        report += f"""
## Detailed Metrics

### 📊 Diversity Metrics
- **Title Diversity Score**: {diversity.get('title_diversity', 0):.2%}
- **Unique Title Ratio**: {diversity.get('unique_title_ratio', 0):.2%}
- **Average Titles per Trial**: {diversity.get('avg_titles_per_trial', 0):.1f}

### 📈 Stability Metrics
- **Confidence Score CV**: {stability.get('confidence_cv', 0):.2%}
  - Mean: {stability.get('confidence_mean', 0):.2f}
  - Std Dev: {stability.get('confidence_std', 0):.2f}
- **Budget CV**: {stability.get('budget_cv', 0):.2%}
  - Mean: €{stability.get('budget_mean', 0):.1f}M
  - Std Dev: €{stability.get('budget_std', 0):.1f}M
- **Timeline Consistency**: {stability.get('timeline_consistency', 0):.2%}

### ✅ Compliance Metrics
- **Overall Compliance**: {compliance.get('avg_compliance', 0):.2%}
- **Error Rate**: {compliance.get('error_rate', 0):.2%}

#### Section Compliance:
"""
        
        for key, value in compliance.items():
            if key.startswith('compliance_') and key != 'avg_compliance':
                section = key.replace('compliance_', '').replace('_', ' ').title()
                report += f"- {section}: {value:.2%}\n"
        
        report += f"""
### ⚡ Performance Metrics
- **Latency**:
  - Mean: {performance.get('latency_mean', 0):.0f}ms
  - P50: {performance.get('latency_p50', 0):.0f}ms
  - P95: {performance.get('latency_p95', 0):.0f}ms
- **Token Usage**:
  - Mean: {performance.get('tokens_mean', 0):.0f} tokens/trial
  - Total: {performance.get('tokens_total', 0):,} tokens
- **API Calls**: {performance.get('api_calls_mean', 0):.1f} calls/trial
- **Estimated Cost**: ${performance.get('estimated_cost_usd', 0):.3f}

## Recommendations

"""
        
        # Generate recommendations based on metrics
        if diversity.get('title_diversity', 0) < 0.5:
            report += "1. **Increase prompt variation**: Add randomization or temperature adjustments to increase output diversity\n"
        
        if stability.get('confidence_cv', 1) > 0.2:
            report += "2. **Stabilize numeric outputs**: Consider adding constraints or examples for numeric fields\n"
        
        if compliance.get('avg_compliance', 0) < 0.8:
            report += "3. **Improve structure compliance**: Strengthen prompt instructions for required sections\n"
        
        if performance.get('latency_p95', 0) > 30000:
            report += "4. **Optimize performance**: Consider reducing max_tokens or implementing caching\n"
        
        report += f"""
## Trial IDs
For detailed investigation, use these trial IDs:
{chr(10).join(f"- {tid}" for tid in assessment['trial_ids'])}
"""
        
        return report