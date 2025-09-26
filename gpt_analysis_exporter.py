#!/usr/bin/env python3
"""
GPT-Ready LLM Performance Analysis Exporter
==========================================

This module generates comprehensive analysis reports from the Enhanced Variance Assessment Dashboard
in formats optimized for GPT model analysis. The exports include detailed explanations of metrics,
their significance, and analytical conclusions about LLM performance.

Usage:
    python gpt_analysis_exporter.py --input dashboard_data.json --output gpt_analysis_report.json
    
Or integrate directly with the dashboard for real-time exports.
"""

import os
import json
import argparse
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

@dataclass
class MetricDefinition:
    """Definition of a metric for GPT understanding"""
    name: str
    category: str
    description: str
    interpretation: str
    good_range: str
    warning_range: str
    critical_range: str
    calculation_method: str

class GPTAnalysisExporter:
    """Export LLM performance analysis in GPT-optimized format"""
    
    def __init__(self):
        self.metric_definitions = self._initialize_metric_definitions()
        self.analysis_frameworks = self._initialize_analysis_frameworks()
    
    def _initialize_metric_definitions(self) -> Dict[str, MetricDefinition]:
        """Initialize comprehensive metric definitions for GPT understanding"""
        
        definitions = {}
        
        # Diversity Metrics
        definitions['title_diversity'] = MetricDefinition(
            name="Title Diversity",
            category="Content Diversity", 
            description="Measures how varied the generated technology trend titles are across multiple trials",
            interpretation="Higher values indicate the LLM generates more unique and creative titles rather than repeating similar concepts",
            good_range="70-100% (0.7-1.0)",
            warning_range="50-70% (0.5-0.7)",
            critical_range="Below 50% (0.5)",
            calculation_method="Ratio of unique titles to total titles generated across trials"
        )
        
        definitions['semantic_drift'] = MetricDefinition(
            name="Semantic Drift",
            category="Content Consistency",
            description="Measures how much the semantic meaning changes across consecutive responses",
            interpretation="Low drift (0-30%) indicates consistent messaging; High drift (70-100%) suggests unstable or incoherent outputs",
            good_range="0-30%",
            warning_range="30-50%", 
            critical_range="Above 50%",
            calculation_method="TF-IDF cosine similarity variance between consecutive responses"
        )
        
        # Quality Metrics
        definitions['confidence_cv'] = MetricDefinition(
            name="Confidence Coefficient of Variation",
            category="Reliability",
            description="Measures the relative variability of confidence scores across trials",
            interpretation="Lower CV indicates consistent confidence levels; Higher CV suggests unstable self-assessment",
            good_range="0-20%",
            warning_range="20-40%",
            critical_range="Above 40%",
            calculation_method="Standard deviation divided by mean of confidence scores"
        )
        
        definitions['pass_at_1'] = MetricDefinition(
            name="Pass@1 Success Rate", 
            category="Task Completion",
            description="Percentage of single attempts that meet quality thresholds",
            interpretation="Higher pass rates indicate reliable performance on first attempt",
            good_range="80-100%",
            warning_range="60-80%",
            critical_range="Below 60%",
            calculation_method="Percentage of trials with confidence scores above threshold (typically 0.7)"
        )
        
        definitions['pass_at_3'] = MetricDefinition(
            name="Pass@3 Success Rate",
            category="Task Completion",
            description="Percentage of 3-attempt sequences where all attempts succeed", 
            interpretation="Measures consistency across multiple attempts; Critical for production reliability",
            good_range="70-100%",
            warning_range="50-70%",
            critical_range="Below 50%",
            calculation_method="Percentage of 3-trial groups where all trials exceed quality threshold"
        )
        
        # Error Detection Metrics
        definitions['hallucination_risk'] = MetricDefinition(
            name="Hallucination Risk Score",
            category="Content Accuracy",
            description="Measures likelihood of generating false or inconsistent information",
            interpretation="Higher scores indicate greater risk of hallucinations and factual errors",
            good_range="0-20%",
            warning_range="20-40%",
            critical_range="Above 40%",
            calculation_method="Variance in response similarity and numerical consistency across trials"
        )
        
        definitions['error_rate'] = MetricDefinition(
            name="Error Rate",
            category="Content Quality",
            description="Percentage of responses containing detectable errors (format, placeholders, truncation)",
            interpretation="Lower error rates indicate higher output quality and reliability",
            good_range="0-10%",
            warning_range="10-25%", 
            critical_range="Above 25%",
            calculation_method="Percentage of responses with format errors, placeholders, or truncation"
        )
        
        # Performance Metrics
        definitions['efficiency_score'] = MetricDefinition(
            name="Efficiency Score",
            category="Performance",
            description="Combined metric of token usage efficiency and time performance",
            interpretation="Higher scores indicate better resource utilization and faster processing",
            good_range="0.7-1.0",
            warning_range="0.4-0.7",
            critical_range="Below 0.4",
            calculation_method="Weighted combination of token efficiency and time efficiency normalized by success rate"
        )
        
        definitions['latency_mean'] = MetricDefinition(
            name="Average Response Latency", 
            category="Performance",
            description="Mean time taken to generate responses",
            interpretation="Lower latency indicates faster processing; Critical for user experience",
            good_range="0-5000ms",
            warning_range="5000-15000ms",
            critical_range="Above 15000ms",
            calculation_method="Average time between request and response completion"
        )
        
        # Advanced Metrics
        definitions['trajectory_uniqueness'] = MetricDefinition(
            name="Reasoning Trajectory Uniqueness",
            category="Reasoning Quality", 
            description="Measures diversity in reasoning steps and thought processes",
            interpretation="Higher uniqueness indicates more varied and thorough reasoning approaches",
            good_range="70-100%",
            warning_range="50-70%",
            critical_range="Below 50%",
            calculation_method="Ratio of unique reasoning steps to total steps across responses"
        )
        
        return definitions
    
    def _initialize_analysis_frameworks(self) -> Dict[str, Dict]:
        """Initialize analysis frameworks for different performance aspects"""
        
        frameworks = {}
        
        # Production Readiness Framework
        frameworks['production_readiness'] = {
            'name': 'Production Readiness Assessment',
            'description': 'Evaluates if the LLM is ready for production deployment',
            'critical_metrics': ['pass_at_1', 'error_rate', 'hallucination_risk'],
            'thresholds': {
                'ready': {'pass_at_1': 80, 'error_rate': 10, 'hallucination_risk': 20},
                'needs_improvement': {'pass_at_1': 60, 'error_rate': 25, 'hallucination_risk': 40},
                'not_ready': {'pass_at_1': 60, 'error_rate': 25, 'hallucination_risk': 40}
            }
        }
        
        # Content Quality Framework  
        frameworks['content_quality'] = {
            'name': 'Content Quality Assessment',
            'description': 'Evaluates the quality and consistency of generated content',
            'critical_metrics': ['title_diversity', 'semantic_drift', 'confidence_cv'],
            'thresholds': {
                'excellent': {'title_diversity': 70, 'semantic_drift': 30, 'confidence_cv': 20},
                'good': {'title_diversity': 50, 'semantic_drift': 50, 'confidence_cv': 40},
                'poor': {'title_diversity': 50, 'semantic_drift': 50, 'confidence_cv': 40}
            }
        }
        
        # Reliability Framework
        frameworks['reliability'] = {
            'name': 'System Reliability Assessment', 
            'description': 'Evaluates consistency and predictability of LLM outputs',
            'critical_metrics': ['pass_at_3', 'confidence_cv', 'semantic_drift'],
            'thresholds': {
                'highly_reliable': {'pass_at_3': 70, 'confidence_cv': 20, 'semantic_drift': 30},
                'moderately_reliable': {'pass_at_3': 50, 'confidence_cv': 40, 'semantic_drift': 50},
                'unreliable': {'pass_at_3': 50, 'confidence_cv': 40, 'semantic_drift': 50}
            }
        }
        
        return frameworks
    
    def generate_comprehensive_gpt_report(self, 
                                        analysis_data: Dict, 
                                        include_raw_data: bool = False,
                                        include_recommendations: bool = True) -> Dict:
        """Generate comprehensive analysis report optimized for GPT understanding"""
        
        report = {
            'report_metadata': {
                'generated_at': datetime.now().isoformat(),
                'report_version': '1.0.0',
                'analysis_scope': f"{len(analysis_data.get('query_analyses', []))} queries analyzed",
                'purpose': 'LLM Performance Analysis for GPT Model Review',
                'instructions_for_gpt': self._generate_gpt_instructions()
            },
            'executive_summary': self._generate_executive_summary(analysis_data),
            'metric_definitions': self._export_metric_definitions(),
            'system_performance_analysis': self._analyze_system_performance(analysis_data),
            'query_level_analysis': self._analyze_individual_queries(analysis_data),
            'comparative_analysis': self._generate_comparative_analysis(analysis_data),
            'framework_assessments': self._apply_assessment_frameworks(analysis_data),
            'trend_analysis': self._analyze_performance_trends(analysis_data),
            'actionable_insights': self._generate_actionable_insights(analysis_data) if include_recommendations else {},
            'raw_data': analysis_data if include_raw_data else {'note': 'Raw data excluded for brevity'}
        }
        
        return report
    
    def _generate_gpt_instructions(self) -> Dict:
        """Generate instructions for GPT models analyzing this report"""
        
        return {
            'analysis_approach': {
                'primary_focus': 'Evaluate LLM performance patterns, identify strengths and weaknesses',
                'key_questions': [
                    'Is this LLM ready for production use?',
                    'What are the main quality concerns?',
                    'Which metrics show concerning trends?',
                    'What recommendations would improve performance?'
                ]
            },
            'metric_interpretation': {
                'good_performance_indicators': [
                    'High Pass@1 rates (80%+)',
                    'Low error rates (<10%)',
                    'Low hallucination risk (<20%)',
                    'High content diversity (70%+)',
                    'Low confidence CV (<20%)'
                ],
                'warning_signs': [
                    'Declining success rates over time',
                    'High semantic drift (>50%)',
                    'Inconsistent confidence scores',
                    'Increasing error rates'
                ]
            },
            'analysis_priorities': {
                'critical': ['Production readiness', 'Safety and reliability', 'Error rates'],
                'important': ['Content quality', 'Performance efficiency', 'Consistency'],
                'informational': ['Detailed breakdowns', 'Historical trends', 'Comparative metrics']
            },
            'reporting_guidelines': {
                'structure': 'Provide executive summary, key findings, recommendations, and supporting details',
                'tone': 'Professional, data-driven, actionable',
                'focus': 'Actionable insights rather than just metric descriptions'
            }
        }
    
    def _generate_executive_summary(self, analysis_data: Dict) -> Dict:
        """Generate executive summary of LLM performance"""
        
        system_metrics = analysis_data.get('system_metrics', {})
        query_analyses = analysis_data.get('query_analyses', [])
        
        # Calculate key performance indicators
        avg_pass_at_1 = np.mean([
            qa.get('metrics', {}).get('advanced_variance', {}).get('pass_at_1', 0) 
            for qa in query_analyses
        ]) if query_analyses else 0
        
        avg_error_rate = np.mean([
            np.mean(list(qa.get('metrics', {}).get('error_analysis', {}).values())) if qa.get('metrics', {}).get('error_analysis') else 0
            for qa in query_analyses  
        ]) if query_analyses else 0
        
        avg_hallucination_risk = np.mean([
            qa.get('metrics', {}).get('hallucination_metrics', {}).get('selfcheck_variance', 0)
            for qa in query_analyses
        ]) if query_analyses else 0
        
        # Determine overall status
        if avg_pass_at_1 >= 80 and avg_error_rate <= 10 and avg_hallucination_risk <= 20:
            overall_status = 'PRODUCTION_READY'
            status_description = 'LLM demonstrates strong performance across key reliability metrics'
        elif avg_pass_at_1 >= 60 and avg_error_rate <= 25 and avg_hallucination_risk <= 40:
            overall_status = 'NEEDS_IMPROVEMENT'
            status_description = 'LLM shows acceptable performance but requires optimization before production'
        else:
            overall_status = 'NOT_READY'
            status_description = 'LLM performance is below production standards and requires significant improvements'
        
        return {
            'overall_status': overall_status,
            'status_description': status_description,
            'key_metrics': {
                'total_queries_analyzed': len(query_analyses),
                'total_trials': analysis_data.get('export_metadata', {}).get('total_records', 0),
                'average_pass_at_1_rate': round(avg_pass_at_1, 1),
                'average_error_rate': round(avg_error_rate, 1),
                'average_hallucination_risk': round(avg_hallucination_risk, 1),
                'system_confidence_cv': round(system_metrics.get('confidence_cv', 0) * 100, 1)
            },
            'critical_findings': self._identify_critical_findings(query_analyses),
            'top_recommendations': self._generate_top_recommendations(overall_status, avg_pass_at_1, avg_error_rate, avg_hallucination_risk)
        }
    
    def _identify_critical_findings(self, query_analyses: List[Dict]) -> List[str]:
        """Identify critical performance findings"""
        
        findings = []
        
        # Check for queries with very low performance
        poor_performers = [
            qa for qa in query_analyses
            if qa.get('metrics', {}).get('advanced_variance', {}).get('pass_at_1', 0) < 50
        ]
        
        if poor_performers:
            findings.append(f"{len(poor_performers)} queries show critically low success rates (<50%)")
        
        # Check for high hallucination risk
        high_risk_queries = [
            qa for qa in query_analyses  
            if qa.get('metrics', {}).get('hallucination_metrics', {}).get('selfcheck_variance', 0) > 60
        ]
        
        if high_risk_queries:
            findings.append(f"{len(high_risk_queries)} queries show high hallucination risk")
        
        # Check for consistency issues
        inconsistent_queries = [
            qa for qa in query_analyses
            if qa.get('metrics', {}).get('basic_metrics', {}).get('confidence_cv', 0) > 0.5
        ]
        
        if inconsistent_queries:
            findings.append(f"{len(inconsistent_queries)} queries show high confidence variability")
        
        return findings[:5]  # Limit to top 5 critical findings
    
    def _generate_top_recommendations(self, status: str, pass_rate: float, error_rate: float, hallucination_risk: float) -> List[str]:
        """Generate top recommendations based on performance"""
        
        recommendations = []
        
        if pass_rate < 70:
            recommendations.append("Improve prompt engineering to increase success rates")
        
        if error_rate > 15:
            recommendations.append("Implement better output validation and error checking")
        
        if hallucination_risk > 30:
            recommendations.append("Add hallucination detection and mitigation strategies")
        
        if status == 'NOT_READY':
            recommendations.append("Consider model fine-tuning or alternative model architectures")
        
        return recommendations[:3]  # Limit to top 3 recommendations
    
    def _export_metric_definitions(self) -> Dict:
        """Export metric definitions for GPT understanding"""
        
        exported_definitions = {}
        
        for metric_key, definition in self.metric_definitions.items():
            exported_definitions[metric_key] = {
                'name': definition.name,
                'category': definition.category,
                'description': definition.description,
                'interpretation_guide': definition.interpretation,
                'performance_ranges': {
                    'good': definition.good_range,
                    'warning': definition.warning_range,
                    'critical': definition.critical_range
                },
                'calculation_method': definition.calculation_method
            }
        
        return exported_definitions
    
    def _analyze_system_performance(self, analysis_data: Dict) -> Dict:
        """Analyze overall system performance"""
        
        system_metrics = analysis_data.get('system_metrics', {})
        query_analyses = analysis_data.get('query_analyses', [])
        
        # Aggregate metrics across all queries
        aggregated_metrics = {
            'pass_at_1_scores': [],
            'error_rates': [],
            'hallucination_risks': [],
            'efficiency_scores': [],
            'confidence_cvs': []
        }
        
        for qa in query_analyses:
            metrics = qa.get('metrics', {})
            
            # Collect values for aggregation
            if metrics.get('advanced_variance', {}).get('pass_at_1'):
                aggregated_metrics['pass_at_1_scores'].append(metrics['advanced_variance']['pass_at_1'])
            
            if metrics.get('error_analysis'):
                error_rate = np.mean(list(metrics['error_analysis'].values()))
                aggregated_metrics['error_rates'].append(error_rate)
            
            if metrics.get('hallucination_metrics', {}).get('selfcheck_variance'):
                aggregated_metrics['hallucination_risks'].append(metrics['hallucination_metrics']['selfcheck_variance'])
            
            if metrics.get('efficiency_metrics', {}).get('efficiency_score'):
                aggregated_metrics['efficiency_scores'].append(metrics['efficiency_metrics']['efficiency_score'])
            
            if metrics.get('basic_metrics', {}).get('confidence_cv'):
                aggregated_metrics['confidence_cvs'].append(metrics['basic_metrics']['confidence_cv'])
        
        # Calculate statistics
        performance_statistics = {}
        for metric_name, values in aggregated_metrics.items():
            if values:
                performance_statistics[metric_name] = {
                    'mean': float(np.mean(values)),
                    'std': float(np.std(values)),
                    'min': float(np.min(values)),
                    'max': float(np.max(values)),
                    'median': float(np.median(values)),
                    'percentile_25': float(np.percentile(values, 25)),
                    'percentile_75': float(np.percentile(values, 75))
                }
        
        return {
            'system_metrics': system_metrics,
            'aggregated_performance': performance_statistics,
            'performance_distribution': self._analyze_performance_distribution(aggregated_metrics),
            'outlier_analysis': self._identify_performance_outliers(query_analyses)
        }
    
    def _analyze_performance_distribution(self, aggregated_metrics: Dict) -> Dict:
        """Analyze distribution of performance metrics"""
        
        distribution_analysis = {}
        
        for metric_name, values in aggregated_metrics.items():
            if not values:
                continue
            
            # Performance tier distribution
            if metric_name == 'pass_at_1_scores':
                excellent = len([v for v in values if v >= 80])
                good = len([v for v in values if 60 <= v < 80])
                poor = len([v for v in values if v < 60])
                
                distribution_analysis[metric_name] = {
                    'excellent_performance': {'count': excellent, 'percentage': excellent/len(values)*100},
                    'good_performance': {'count': good, 'percentage': good/len(values)*100},
                    'poor_performance': {'count': poor, 'percentage': poor/len(values)*100}
                }
            
            elif metric_name == 'error_rates':
                low = len([v for v in values if v <= 10])
                medium = len([v for v in values if 10 < v <= 25])
                high = len([v for v in values if v > 25])
                
                distribution_analysis[metric_name] = {
                    'low_error_rate': {'count': low, 'percentage': low/len(values)*100},
                    'medium_error_rate': {'count': medium, 'percentage': medium/len(values)*100},
                    'high_error_rate': {'count': high, 'percentage': high/len(values)*100}
                }
        
        return distribution_analysis
    
    def _identify_performance_outliers(self, query_analyses: List[Dict]) -> Dict:
        """Identify performance outliers for investigation"""
        
        outliers = {
            'top_performers': [],
            'poor_performers': [],
            'inconsistent_performers': []
        }
        
        for qa in query_analyses:
            query_info = qa.get('query_info', {})
            metrics = qa.get('metrics', {})
            
            pass_at_1 = metrics.get('advanced_variance', {}).get('pass_at_1', 0)
            confidence_cv = metrics.get('basic_metrics', {}).get('confidence_cv', 0)
            
            query_summary = {
                'use_case': query_info.get('use_case', 'Unknown'),
                'sector': query_info.get('sector', 'Unknown'),
                'trial_count': query_info.get('trial_count', 0),
                'pass_at_1': pass_at_1,
                'confidence_cv': confidence_cv
            }
            
            # Identify outliers
            if pass_at_1 >= 90:
                outliers['top_performers'].append(query_summary)
            elif pass_at_1 <= 30:
                outliers['poor_performers'].append(query_summary)
            
            if confidence_cv > 0.6:  # Very high variability
                outliers['inconsistent_performers'].append(query_summary)
        
        # Sort and limit results
        outliers['top_performers'] = sorted(outliers['top_performers'], key=lambda x: x['pass_at_1'], reverse=True)[:5]
        outliers['poor_performers'] = sorted(outliers['poor_performers'], key=lambda x: x['pass_at_1'])[:5]
        outliers['inconsistent_performers'] = sorted(outliers['inconsistent_performers'], key=lambda x: x['confidence_cv'], reverse=True)[:5]
        
        return outliers
    
    def _analyze_individual_queries(self, analysis_data: Dict) -> List[Dict]:
        """Analyze individual query performance"""
        
        query_analyses = analysis_data.get('query_analyses', [])
        analyzed_queries = []
        
        for qa in query_analyses:
            query_info = qa.get('query_info', {})
            metrics = qa.get('metrics', {})
            
            # Extract key metrics
            basic_metrics = metrics.get('basic_metrics', {})
            advanced_metrics = metrics.get('advanced_variance', {})
            hallucination_metrics = metrics.get('hallucination_metrics', {})
            error_analysis = metrics.get('error_analysis', {})
            
            # Performance assessment
            pass_at_1 = advanced_metrics.get('pass_at_1', 0)
            
            if pass_at_1 >= 80:
                performance_rating = 'Excellent'
            elif pass_at_1 >= 60:
                performance_rating = 'Good'
            elif pass_at_1 >= 40:
                performance_rating = 'Fair'
            else:
                performance_rating = 'Poor'
            
            # Key insights for this query
            insights = []
            
            if basic_metrics.get('confidence_cv', 0) > 0.4:
                insights.append('High confidence variability indicates unstable performance')
            
            if hallucination_metrics.get('selfcheck_variance', 0) > 50:
                insights.append('High hallucination risk detected')
            
            if error_analysis and np.mean(list(error_analysis.values())) > 20:
                insights.append('Significant error rates in responses')
            
            analyzed_queries.append({
                'query_identifier': f"{query_info.get('use_case', 'Unknown')} - {query_info.get('sector', 'Unknown')}",
                'query_details': query_info,
                'performance_rating': performance_rating,
                'key_metrics': {
                    'pass_at_1': pass_at_1,
                    'confidence_mean': basic_metrics.get('confidence_mean', 0),
                    'confidence_cv': basic_metrics.get('confidence_cv', 0) * 100,
                    'hallucination_risk': hallucination_metrics.get('selfcheck_variance', 0),
                    'semantic_drift': advanced_metrics.get('semantic_drift', 0)
                },
                'performance_insights': insights,
                'raw_metrics': metrics  # Include for detailed analysis if needed
            })
        
        return analyzed_queries
    
    def _generate_comparative_analysis(self, analysis_data: Dict) -> Dict:
        """Generate comparative analysis across queries and metrics"""
        
        query_analyses = analysis_data.get('query_analyses', [])
        
        if len(query_analyses) < 2:
            return {'note': 'Insufficient data for comparative analysis'}
        
        # Group by use case and sector
        use_case_performance = {}
        sector_performance = {}
        
        for qa in query_analyses:
            query_info = qa.get('query_info', {})
            metrics = qa.get('metrics', {})
            
            use_case = query_info.get('use_case', 'Unknown')
            sector = query_info.get('sector', 'Unknown')
            
            pass_at_1 = metrics.get('advanced_variance', {}).get('pass_at_1', 0)
            
            # Aggregate by use case
            if use_case not in use_case_performance:
                use_case_performance[use_case] = []
            use_case_performance[use_case].append(pass_at_1)
            
            # Aggregate by sector
            if sector not in sector_performance:
                sector_performance[sector] = []
            sector_performance[sector].append(pass_at_1)
        
        # Calculate comparative statistics
        comparative_results = {
            'use_case_comparison': {},
            'sector_comparison': {},
            'performance_ranking': {}
        }
        
        # Use case comparison
        for use_case, scores in use_case_performance.items():
            comparative_results['use_case_comparison'][use_case] = {
                'average_pass_at_1': float(np.mean(scores)),
                'query_count': len(scores),
                'performance_std': float(np.std(scores))
            }
        
        # Sector comparison
        for sector, scores in sector_performance.items():
            comparative_results['sector_comparison'][sector] = {
                'average_pass_at_1': float(np.mean(scores)),
                'query_count': len(scores),
                'performance_std': float(np.std(scores))
            }
        
        # Performance ranking
        use_case_rankings = sorted(
            comparative_results['use_case_comparison'].items(),
            key=lambda x: x[1]['average_pass_at_1'],
            reverse=True
        )
        
        comparative_results['performance_ranking'] = {
            'best_use_case': use_case_rankings[0][0] if use_case_rankings else 'N/A',
            'worst_use_case': use_case_rankings[-1][0] if use_case_rankings else 'N/A',
            'use_case_rankings': [(uc, data['average_pass_at_1']) for uc, data in use_case_rankings]
        }
        
        return comparative_results
    
    def _apply_assessment_frameworks(self, analysis_data: Dict) -> Dict:
        """Apply assessment frameworks to evaluate LLM performance"""
        
        framework_results = {}
        query_analyses = analysis_data.get('query_analyses', [])
        
        for framework_name, framework in self.analysis_frameworks.items():
            framework_results[framework_name] = {
                'name': framework['name'],
                'description': framework['description'],
                'assessment_results': self._assess_framework_performance(query_analyses, framework),
                'overall_rating': '',
                'key_findings': []
            }
        
        return framework_results
    
    def _assess_framework_performance(self, query_analyses: List[Dict], framework: Dict) -> Dict:
        """Assess performance against a specific framework"""
        
        critical_metrics = framework['critical_metrics']
        thresholds = framework['thresholds']
        
        assessment_results = {
            'metrics_assessment': {},
            'queries_by_tier': {'excellent': 0, 'good': 0, 'poor': 0},
            'overall_score': 0
        }
        
        # Collect metric values
        metric_values = {metric: [] for metric in critical_metrics}
        
        for qa in query_analyses:
            metrics = qa.get('metrics', {})
            
            for metric in critical_metrics:
                value = self._extract_metric_value(metrics, metric)
                if value is not None:
                    metric_values[metric].append(value)
        
        # Assess each metric
        for metric, values in metric_values.items():
            if values:
                avg_value = np.mean(values)
                assessment_results['metrics_assessment'][metric] = {
                    'average_value': float(avg_value),
                    'performance_tier': self._determine_performance_tier(avg_value, thresholds, metric)
                }
        
        return assessment_results
    
    def _extract_metric_value(self, metrics: Dict, metric_name: str) -> Optional[float]:
        """Extract specific metric value from metrics dict"""
        
        if metric_name == 'pass_at_1':
            return metrics.get('advanced_variance', {}).get('pass_at_1', 0)
        elif metric_name == 'error_rate':
            error_analysis = metrics.get('error_analysis', {})
            return np.mean(list(error_analysis.values())) if error_analysis else 0
        elif metric_name == 'hallucination_risk':
            return metrics.get('hallucination_metrics', {}).get('selfcheck_variance', 0)
        elif metric_name == 'confidence_cv':
            return metrics.get('basic_metrics', {}).get('confidence_cv', 0) * 100
        elif metric_name == 'semantic_drift':
            return metrics.get('advanced_variance', {}).get('semantic_drift', 0)
        elif metric_name == 'title_diversity':
            return metrics.get('diversity', {}).get('title_diversity', 0) * 100
        
        return None
    
    def _determine_performance_tier(self, value: float, thresholds: Dict, metric_name: str) -> str:
        """Determine performance tier based on thresholds"""
        
        # Implementation depends on metric type (higher-is-better vs lower-is-better)
        if metric_name in ['pass_at_1', 'title_diversity']:  # Higher is better
            if value >= thresholds.get('excellent', {}).get(metric_name, 80):
                return 'excellent'
            elif value >= thresholds.get('good', {}).get(metric_name, 60):
                return 'good'
            else:
                return 'poor'
        else:  # Lower is better (error rates, etc.)
            if value <= thresholds.get('excellent', {}).get(metric_name, 20):
                return 'excellent'
            elif value <= thresholds.get('good', {}).get(metric_name, 40):
                return 'good'
            else:
                return 'poor'
    
    def _analyze_performance_trends(self, analysis_data: Dict) -> Dict:
        """Analyze performance trends over time if data is available"""
        
        # This is a placeholder for trend analysis
        # In practice, you'd need temporal data to perform meaningful trend analysis
        
        return {
            'note': 'Trend analysis requires temporal data across multiple time periods',
            'recommendations': 'Implement regular performance monitoring to enable trend analysis',
            'future_considerations': [
                'Track performance metrics over time',
                'Monitor for performance degradation',
                'Identify seasonal or usage-based patterns'
            ]
        }
    
    def _generate_actionable_insights(self, analysis_data: Dict) -> Dict:
        """Generate actionable insights and recommendations"""
        
        query_analyses = analysis_data.get('query_analyses', [])
        
        insights = {
            'immediate_actions': [],
            'medium_term_improvements': [],
            'long_term_strategy': [],
            'specific_recommendations': {}
        }
        
        # Analyze common failure patterns
        poor_performers = [
            qa for qa in query_analyses
            if qa.get('metrics', {}).get('advanced_variance', {}).get('pass_at_1', 0) < 60
        ]
        
        if poor_performers:
            insights['immediate_actions'].append({
                'action': 'Investigate poor-performing queries',
                'priority': 'High',
                'description': f'{len(poor_performers)} queries show success rates below 60%',
                'next_steps': ['Review query complexity', 'Analyze common failure patterns', 'Consider prompt optimization']
            })
        
        # Check for consistency issues
        inconsistent_queries = [
            qa for qa in query_analyses
            if qa.get('metrics', {}).get('basic_metrics', {}).get('confidence_cv', 0) > 0.4
        ]
        
        if inconsistent_queries:
            insights['medium_term_improvements'].append({
                'improvement': 'Enhance response consistency',
                'priority': 'Medium',
                'description': f'{len(inconsistent_queries)} queries show high variability',
                'approach': ['Implement response validation', 'Consider ensemble methods', 'Improve prompt stability']
            })
        
        return insights
    
    def export_for_gpt_analysis(self, 
                               analysis_data: Dict, 
                               output_file: str = None,
                               format: str = 'json',
                               include_raw_data: bool = False) -> str:
        """Export comprehensive analysis for GPT model review"""
        
        if not output_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"gpt_llm_analysis_{timestamp}.{format}"
        
        # Generate comprehensive report
        report = self.generate_comprehensive_gpt_report(
            analysis_data, 
            include_raw_data=include_raw_data
        )
        
        # Export based on format
        if format.lower() == 'json':
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, default=str, ensure_ascii=False)
        
        elif format.lower() == 'markdown':
            markdown_content = self._convert_report_to_markdown(report)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
        
        print(f"✅ GPT-ready analysis report exported to: {output_file}")
        print(f"📊 Report contains analysis of {len(report['query_level_analysis'])} queries")
        print(f"🎯 Overall status: {report['executive_summary']['overall_status']}")
        
        return output_file
    
    def _convert_report_to_markdown(self, report: Dict) -> str:
        """Convert report to markdown format for better readability"""
        
        markdown = f"""# LLM Performance Analysis Report
Generated: {report['report_metadata']['generated_at']}

## Executive Summary
**Overall Status:** {report['executive_summary']['overall_status']}

{report['executive_summary']['status_description']}

### Key Performance Indicators
- **Pass@1 Rate:** {report['executive_summary']['key_metrics']['average_pass_at_1_rate']}%
- **Error Rate:** {report['executive_summary']['key_metrics']['average_error_rate']}%
- **Hallucination Risk:** {report['executive_summary']['key_metrics']['average_hallucination_risk']}%

### Critical Findings
"""
        
        for finding in report['executive_summary']['critical_findings']:
            markdown += f"- {finding}\n"
        
        markdown += "\n### Top Recommendations\n"
        for rec in report['executive_summary']['top_recommendations']:
            markdown += f"- {rec}\n"
        
        markdown += "\n## Detailed Analysis\n"
        markdown += "*For complete analysis details, see the JSON export.*\n"
        
        return markdown


def main():
    parser = argparse.ArgumentParser(description='Export LLM analysis for GPT review')
    
    parser.add_argument('--input', '-i', required=True,
                       help='Input analysis data file (JSON)')
    
    parser.add_argument('--output', '-o',
                       help='Output filename (auto-generated if not specified)')
    
    parser.add_argument('--format', choices=['json', 'markdown'], default='json',
                       help='Export format')
    
    parser.add_argument('--include-raw-data', action='store_true',
                       help='Include raw analysis data in export')
    
    args = parser.parse_args()
    
    # Load analysis data
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            analysis_data = json.load(f)
    except Exception as e:
        print(f"❌ Error loading input file: {e}")
        return
    
    # Export analysis
    exporter = GPTAnalysisExporter()
    output_file = exporter.export_for_gpt_analysis(
        analysis_data,
        output_file=args.output,
        format=args.format,
        include_raw_data=args.include_raw_data
    )
    
    print(f"\n📋 Analysis exported successfully!")
    print(f"📁 File: {output_file}")
    print(f"💡 This report is optimized for GPT model analysis and contains:")
    print("   • Comprehensive metric explanations")
    print("   • Performance assessments")
    print("   • Actionable recommendations")
    print("   • Structured data for automated analysis")


if __name__ == "__main__":
    main()