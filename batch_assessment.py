# batch_assessment.py

import json
import time
from datetime import datetime
from llm_quality_assessment import LLMQualityAssessor, TrialInput
from Final_Structured_app import generate_trends

class BatchAssessor:
    """Run assessments for multiple input combinations"""
    
    def __init__(self):
        self.assessor = LLMQualityAssessor()
        
    def run_batch(self, test_cases_file: str, trials_per_case: int = 5):
        """Run batch assessment from JSON file"""
        
        with open(test_cases_file, 'r') as f:
            test_cases = json.load(f)
        
        results = []
        
        print(f"Running batch assessment for {len(test_cases)} test cases")
        print(f"Trials per case: {trials_per_case}")
        print("=" * 60)
        
        for i, case in enumerate(test_cases):
            print(f"\nTest Case {i+1}/{len(test_cases)}")
            print(f"- Use Case: {case['use_case']}")
            print(f"- Sector: {case['sector']}")
            print(f"- Demand: {case['demand']}")
            
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
            
            results.append({
                'case': case,
                'assessment': assessment
            })
            
            # Delay between test cases
            if i < len(test_cases) - 1:
                print("\nWaiting 5 seconds before next test case...")
                time.sleep(5)
        
        # Generate batch report
        self.generate_batch_report(results)
        
        return results
    
    def generate_batch_report(self, results):
        """Generate comprehensive batch report"""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = f"batch_assessment_report_{timestamp}.md"
        
        report = f"""# Batch LLM Assessment Report
Generated: {datetime.now().isoformat()}

## Summary
- **Total Test Cases**: {len(results)}
- **Trials per Case**: {results[0]['assessment']['num_trials'] if results else 0}
- **Total Trials**: {sum(r['assessment']['num_trials'] for r in results)}

## Test Case Results

"""
        
        # Summary table
        report += "| Use Case | Sector | Demand | Diversity | Compliance | Latency (ms) | Cost ($) |\n"
        report += "|----------|--------|--------|-----------|------------|--------------|----------|\n"
        
        total_cost = 0
        
        for r in results:
            case = r['case']
            metrics = r['assessment']['metrics']
            
            diversity = metrics['diversity'].get('title_diversity', 0)
            compliance = metrics['compliance'].get('avg_compliance', 0)
            latency = metrics['performance'].get('latency_mean', 0)
            cost = metrics['performance'].get('estimated_cost_usd', 0)
            
            total_cost += cost
            
            report += f"| {case['use_case']} | {case['sector']} | {case['demand']} | "
            report += f"{diversity:.2%} | {compliance:.2%} | {latency:.0f} | ${cost:.3f} |\n"
        
        report += f"\n**Total Assessment Cost**: ${total_cost:.2f}\n"
        
        # Detailed results
        report += "\n## Detailed Results\n"
        
        for i, r in enumerate(results):
            report += f"\n### Test Case {i+1}\n"
            report += self.assessor.generate_report(r['assessment'])
            report += "\n---\n"
       
       # Comparative analysis
        report += self.generate_comparative_analysis(results)
       
       # Save report
        with open(report_file, 'w') as f:
           f.write(report)
       
        print(f"\n✓ Batch report saved to: {report_file}")
       
       # Also save raw data
        data_file = f"batch_assessment_data_{timestamp}.json"
        with open(data_file, 'w') as f:
           json.dump(results, f, indent=2, default=str)
       
        print(f"✓ Raw data saved to: {data_file}")
   
    def generate_comparative_analysis(self, results):
       """Generate comparative analysis across test cases"""
       
       report = "\n## Comparative Analysis\n\n"
       
       # Collect metrics across all cases
       all_metrics = {
           'diversity': [],
           'compliance': [],
           'latency': [],
           'confidence_cv': [],
           'budget_cv': []
       }
       
       for r in results:
           metrics = r['assessment']['metrics']
           all_metrics['diversity'].append(metrics['diversity'].get('title_diversity', 0))
           all_metrics['compliance'].append(metrics['compliance'].get('avg_compliance', 0))
           all_metrics['latency'].append(metrics['performance'].get('latency_mean', 0))
           all_metrics['confidence_cv'].append(metrics['stability'].get('confidence_cv', 0))
           all_metrics['budget_cv'].append(metrics['stability'].get('budget_cv', 0))
       
       # Statistical summary
       import numpy as np
       
       report += "### Statistical Summary\n\n"
       report += "| Metric | Mean | Std Dev | Min | Max |\n"
       report += "|--------|------|---------|-----|-----|\n"
       
       for metric_name, values in all_metrics.items():
           if values:
               mean_val = np.mean(values)
               std_val = np.std(values)
               min_val = np.min(values)
               max_val = np.max(values)
               
               if metric_name in ['diversity', 'compliance']:
                   report += f"| {metric_name.title()} | {mean_val:.2%} | {std_val:.2%} | {min_val:.2%} | {max_val:.2%} |\n"
               elif metric_name == 'latency':
                   report += f"| {metric_name.title()} | {mean_val:.0f}ms | {std_val:.0f}ms | {min_val:.0f}ms | {max_val:.0f}ms |\n"
               else:
                   report += f"| {metric_name.replace('_', ' ').title()} | {mean_val:.3f} | {std_val:.3f} | {min_val:.3f} | {max_val:.3f} |\n"
       
       # Identify best and worst performers
       report += "\n### Performance Rankings\n\n"
       
       # Best diversity
       best_diversity_idx = np.argmax(all_metrics['diversity'])
       worst_diversity_idx = np.argmin(all_metrics['diversity'])
       
       report += f"**Best Diversity**: Test Case {best_diversity_idx + 1} "
       report += f"({results[best_diversity_idx]['case']['use_case']}) - "
       report += f"{all_metrics['diversity'][best_diversity_idx]:.2%}\n\n"
       
       report += f"**Worst Diversity**: Test Case {worst_diversity_idx + 1} "
       report += f"({results[worst_diversity_idx]['case']['use_case']}) - "
       report += f"{all_metrics['diversity'][worst_diversity_idx]:.2%}\n\n"
       
       # Best compliance
       best_compliance_idx = np.argmax(all_metrics['compliance'])
       worst_compliance_idx = np.argmin(all_metrics['compliance'])
       
       report += f"**Best Compliance**: Test Case {best_compliance_idx + 1} "
       report += f"({results[best_compliance_idx]['case']['use_case']}) - "
       report += f"{all_metrics['compliance'][best_compliance_idx]:.2%}\n\n"
       
       report += f"**Worst Compliance**: Test Case {worst_compliance_idx + 1} "
       report += f"({results[worst_compliance_idx]['case']['use_case']}) - "
       report += f"{all_metrics['compliance'][worst_compliance_idx]:.2%}\n\n"
       
       return report

# Example test cases file (test_cases.json)
"""
[
   {
       "use_case": "People mover mobility",
       "sector": "RoboTaxi",
       "demand": "navigation"
   },
   {
       "use_case": "Cargo transportation",
       "sector": "Autonomous trucks",
       "demand": "efficiency"
   },
   {
       "use_case": "Last-mile delivery",
       "sector": "Delivery robots",
       "demand": "reliability"
   }
]
"""

if __name__ == "__main__":
   import argparse
   
   parser = argparse.ArgumentParser(description='Run batch LLM assessment')
   parser.add_argument('--test-cases', required=True, help='JSON file with test cases')
   parser.add_argument('--trials', type=int, default=5, help='Trials per test case')
   
   args = parser.parse_args()
   
   assessor = BatchAssessor()
   assessor.run_batch(args.test_cases, args.trials)