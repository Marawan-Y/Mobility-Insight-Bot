# assessment_runner.py

import sys
import argparse
from llm_quality_assessment import LLMQualityAssessor, TrialInput

# Import your app's generate_trends function
sys.path.append('.')
from Final_Structured_app import generate_trends

def main():
    parser = argparse.ArgumentParser(description='Run LLM quality assessment')
    parser.add_argument('--use-case', required=True, help='Use case for assessment')
    parser.add_argument('--sector', required=True, help='Sector for assessment')
    parser.add_argument('--demand', required=True, help='Demand for assessment')
    parser.add_argument('--trials', type=int, default=5, help='Number of trials to run')
    parser.add_argument('--output', default='assessment_report.md', help='Output report file')
    
    args = parser.parse_args()
    
    # Create assessor
    assessor = LLMQualityAssessor()
    
    # Create trial input
    trial_input = TrialInput(
        use_case=args.use_case,
        sector=args.sector,
        demand=args.demand
    )
    
    # Run assessment
    assessment = assessor.run_assessment_suite(
        trial_input,
        args.trials,
        generate_trends
    )
    
    # Generate report
    report = assessor.generate_report(assessment)
    
    # Save report
    with open(args.output, 'w') as f:
        f.write(report)
    
    print(f"\n✓ Assessment complete! Report saved to: {args.output}")
    
    # Print summary
    print("\nSummary:")
    print(f"- Diversity Score: {assessment['metrics']['diversity'].get('title_diversity', 0):.2%}")
    print(f"- Compliance Rate: {assessment['metrics']['compliance'].get('avg_compliance', 0):.2%}")
    print(f"- Avg Latency: {assessment['metrics']['performance'].get('latency_mean', 0):.0f}ms")
    print(f"- Total Cost: ${assessment['metrics']['performance'].get('estimated_cost_usd', 0):.3f}")

if __name__ == "__main__":
    main()