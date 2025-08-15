# regression_testing.py

import json
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple
from llm_quality_assessment import LLMQualityAssessor, TrialInput

class RegressionTester:
    """Automated regression testing for LLM outputs"""
    
    def __init__(self, baseline_file: str = None):
        self.assessor = LLMQualityAssessor()
        self.baseline = self.load_baseline(baseline_file) if baseline_file else {}
        
    def load_baseline(self, filename: str) -> Dict:
        """Load baseline metrics from file"""
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def save_baseline(self, filename: str):
        """Save current results as baseline"""
        with open(filename, 'w') as f:
            json.dump(self.baseline, f, indent=2)
    
    def run_regression_test(
        self,
        test_cases: List[Dict],
        trials_per_case: int = 3,
        threshold_settings: Dict = None
    ) -> Dict:
        """Run regression tests against baseline"""
        
        if not threshold_settings:
            threshold_settings = {
                'diversity_drop': 0.2,      # Max allowed drop in diversity
                'compliance_drop': 0.1,     # Max allowed drop in compliance
                'latency_increase': 1.5,    # Max allowed latency multiplier
                'cost_increase': 1.2        # Max allowed cost multiplier
            }
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'test_cases': len(test_cases),
            'trials_per_case': trials_per_case,
            'passed': 0,
            'failed': 0,
            'warnings': 0,
            'details': []
        }
        
        from Final_Structured_app import generate_trends
        
        for case in test_cases:
            print(f"\nTesting: {case['use_case']} / {case['sector']} / {case['demand']}")
            
            # Create unique key for baseline comparison
            case_key = f"{case['use_case']}:{case['sector']}:{case['demand']}"
            
            # Run assessment
            trial_input = TrialInput(
                use_case=case['use_case'],
                sector=case['sector'],
                demand=case['demand']
            )
            
            assessment = self.assessor.run_assessment_suite(
                trial_input,
                trials_per_case,
                generate_trends
            )
            
            # Compare with baseline
            test_result = self.compare_with_baseline(
                case_key,
                assessment,
                threshold_settings
            )
            
            # Update results
            if test_result['status'] == 'PASS':
                results['passed'] += 1
            elif test_result['status'] == 'FAIL':
                results['failed'] += 1
            else:  # WARNING
                results['warnings'] += 1
            
            results['details'].append({
                'case': case,
                'result': test_result,
                'metrics': assessment['metrics']
            })
            
            # Update baseline if this is first run
            if case_key not in self.baseline:
                self.baseline[case_key] = {
                    'metrics': assessment['metrics'],
                    'timestamp': datetime.now().isoformat()
                }
        
        # Generate report
        self.generate_regression_report(results)
        
        return results
    
    def compare_with_baseline(
        self,
        case_key: str,
        assessment: Dict,
        thresholds: Dict
    ) -> Dict:
        """Compare current results with baseline"""
        
        result = {
            'status': 'PASS',
            'issues': [],
            'improvements': []
        }
        
        if case_key not in self.baseline:
            result['status'] = 'NEW'
            result['issues'].append("No baseline data available")
            return result
        
        baseline_metrics = self.baseline[case_key]['metrics']
        current_metrics = assessment['metrics']
        
        # Check diversity
        baseline_diversity = baseline_metrics['diversity'].get('title_diversity', 0)
        current_diversity = current_metrics['diversity'].get('title_diversity', 0)
        
        if current_diversity < baseline_diversity - thresholds['diversity_drop']:
            result['status'] = 'FAIL'
            result['issues'].append(
                f"Diversity dropped from {baseline_diversity:.2%} to {current_diversity:.2%}"
            )
        elif current_diversity > baseline_diversity + 0.1:
            result['improvements'].append(
                f"Diversity improved from {baseline_diversity:.2%} to {current_diversity:.2%}"
            )
        
        # Check compliance
        baseline_compliance = baseline_metrics['compliance'].get('avg_compliance', 0)
        current_compliance = current_metrics['compliance'].get('avg_compliance', 0)
        
        if current_compliance < baseline_compliance - thresholds['compliance_drop']:
            result['status'] = 'FAIL'
            result['issues'].append(
                f"Compliance dropped from {baseline_compliance:.2%} to {current_compliance:.2%}"
            )
        
        # Check latency
        baseline_latency = baseline_metrics['performance'].get('latency_mean', 0)
        current_latency = current_metrics['performance'].get('latency_mean', 0)
        
        if current_latency > baseline_latency * thresholds['latency_increase']:
            result['status'] = 'WARNING' if result['status'] == 'PASS' else result['status']
            result['issues'].append(
                f"Latency increased from {baseline_latency:.0f}ms to {current_latency:.0f}ms"
            )
        
        # Check cost
        baseline_cost = baseline_metrics['performance'].get('estimated_cost_usd', 0)
        current_cost = current_metrics['performance'].get('estimated_cost_usd', 0)
        
        if current_cost > baseline_cost * thresholds['cost_increase']:
            result['status'] = 'WARNING' if result['status'] == 'PASS' else result['status']
            result['issues'].append(
                f"Cost increased from ${baseline_cost:.3f} to ${current_cost:.3f}"
            )
        
        return result
    
    def generate_regression_report(self, results: Dict):
        """Generate regression test report"""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = f"regression_test_report_{timestamp}.md"
        
        report = f"""# LLM Regression Test Report
Generated: {results['timestamp']}

## Summary
- **Total Tests**: {results['test_cases']}
- **Passed**: {results['passed']} ✅
- **Failed**: {results['failed']} ❌
- **Warnings**: {results['warnings']} ⚠️
- **Success Rate**: {(results['passed'] / results['test_cases'] * 100):.1f}%

## Test Results

"""
        
        for detail in results['details']:
            case = detail['case']
            result = detail['result']
            
            status_emoji = {
                'PASS': '✅',
                'FAIL': '❌',
                'WARNING': '⚠️',
                'NEW': '🆕'
            }
            
            report += f"### {case['use_case']} / {case['sector']} / {case['demand']}\n"
            report += f"**Status**: {status_emoji.get(result['status'], '')} {result['status']}\n\n"
            
            if result['issues']:
                report += "**Issues**:\n"
                for issue in result['issues']:
                    report += f"- {issue}\n"
                report += "\n"
            
            if result['improvements']:
                report += "**Improvements**:\n"
                for improvement in result['improvements']:
                    report += f"- {improvement}\n"
                report += "\n"
        
        # Recommendations
        if results['failed'] > 0:
            report += """## Recommendations

1. **Investigate Failed Tests**: Review the specific issues identified in failed tests
2. **Check Recent Changes**: Verify if recent prompt or code changes caused regressions
3. **Update Baselines**: If changes are intentional, update baseline metrics
4. **Monitor Trends**: Set up continuous monitoring for affected metrics
"""
        
        # Save report
        with open(report_file, 'w') as f:
            f.write(report)
        
        print(f"\n✓ Regression test report saved to: {report_file}")

# Example usage
if __name__ == "__main__":
    # Define test cases
    test_cases = [
        {
            "use_case": "People mover mobility",
            "sector": "RoboTaxi",
            "demand": "navigation"
        },
        {
            "use_case": "Cargo transportation",
            "sector": "Autonomous trucks",
            "demand": "efficiency"
        }
    ]
    
    # Run regression tests
    tester = RegressionTester("baseline_metrics.json")
    results = tester.run_regression_test(test_cases, trials_per_case=3)
    
    # Save updated baseline if all tests passed
    if results['failed'] == 0:
        tester.save_baseline("baseline_metrics.json")
        print("✓ Baseline updated with current metrics")