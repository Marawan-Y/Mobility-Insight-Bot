# generate_variance_trials.py

import os
import time
import argparse
from datetime import datetime
import pymysql
from dotenv import load_dotenv
import sys

# Import the main application functions
sys.path.append('.')
from Final_Structured_app import (
    generate_trends, assess_trend, radar_positioning,
    relation_criteria, market_ready_solution, partners_navigation,
    split_trend_blocks, extract_confidence_score
)

load_dotenv()

class VarianceTrialGenerator:
    """Generate multiple trials for the same query to analyze variance"""
    
    def __init__(self):
        self.setup_database_connection()
        
    def setup_database_connection(self):
        """Setup database connection"""
        self.db_config = {
            'host': os.getenv("DB_HOST", "localhost"),
            'port': int(os.getenv("DB_PORT", 3306)),
            'user': os.getenv("DB_USER", "your_user"),
            'password': os.getenv("DB_PASSWORD", "your_pass"),
            'database': os.getenv("DB_NAME", "mobility_bot"),
            'charset': 'utf8mb4'
        }
    
    def run_single_trial(self, use_case: str, sector: str, demand: str, 
                        include_validation: bool = True, 
                        include_implementation: bool = True):
        """Run a single trial for a given query"""
        
        print(f"\n{'='*60}")
        print(f"Running trial for: {use_case} / {sector} / {demand}")
        print(f"{'='*60}")
        
        try:
            # Phase 1: Generate trends
            print("Generating trends...")
            start_time = time.time()
            trends_md = generate_trends(use_case, sector, demand)
            trends_time = time.time() - start_time
            print(f"✓ Trends generated in {trends_time:.2f}s")
            
            if not trends_md:
                print("✗ Failed to generate trends")
                return False
            
            # Parse trends
            titles, blocks = split_trend_blocks(trends_md)
            if not titles:
                print("✗ No trends found in output")
                return False
            
            print(f"✓ Found {len(titles)} trends")
            for i, title in enumerate(titles, 1):
                print(f"  {i}. {title[:60]}...")
            
            # Select first trend for consistency
            selected_trend = titles[0]
            selected_block = blocks[0]
            confidence_score = extract_confidence_score(selected_block)
            
            print(f"\n✓ Selected trend: {selected_trend[:60]}...")
            print(f"✓ Confidence score: {confidence_score}")
            
            # Phase 2: Validation (optional)
            assessment = ""
            radar = ""
            relation = ""
            
            if include_validation:
                print("\nRunning validation...")
                
                start_time = time.time()
                assessment = assess_trend(selected_trend, selected_block)
                assessment_time = time.time() - start_time
                print(f"✓ Assessment completed in {assessment_time:.2f}s")
                
                start_time = time.time()
                radar = radar_positioning(selected_trend, assessment)
                radar_time = time.time() - start_time
                print(f"✓ Radar positioning completed in {radar_time:.2f}s")
                
                start_time = time.time()
                relation = relation_criteria(selected_trend, selected_block)
                relation_time = time.time() - start_time
                print(f"✓ Relation criteria completed in {relation_time:.2f}s")
            
            # Phase 3: Implementation (optional)
            market_solution = ""
            partners = ""
            
            if include_implementation:
                print("\nRunning implementation...")
                
                start_time = time.time()
                market_solution = market_ready_solution(selected_trend, selected_block, sector)
                market_time = time.time() - start_time
                print(f"✓ Market solution completed in {market_time:.2f}s")
                
                start_time = time.time()
                partners = partners_navigation(selected_trend, selected_block)
                partners_time = time.time() - start_time
                print(f"✓ Partners navigation completed in {partners_time:.2f}s")
            
            # Save to database
            print("\nSaving to database...")
            session_id = f"variance_trial_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"
            
            conn = pymysql.connect(**self.db_config)
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO trend_queries (
                            use_case, sector, demand, selected_trend,
                            trend_solutions, trend_assessment, radar_positioning,
                            pestel_tag, market_solution, partners, 
                            confidence_score, session_id
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        use_case, sector, demand, selected_trend,
                        trends_md, assessment, radar, relation,
                        market_solution, partners, confidence_score, session_id
                    ))
                    conn.commit()
                    print(f"✓ Saved with session_id: {session_id}")
                    return True
            finally:
                conn.close()
                
        except Exception as e:
            print(f"✗ Error in trial: {str(e)}")
            return False
    
    def run_multiple_trials(self, use_case: str, sector: str, demand: str,
                           num_trials: int = 5, delay_seconds: int = 5,
                           include_validation: bool = True,
                           include_implementation: bool = True):
        """Run multiple trials for the same query"""
        
        print(f"\n{'='*70}")
        print(f"VARIANCE TRIAL GENERATION")
        print(f"{'='*70}")
        print(f"Query: {use_case} / {sector} / {demand}")
        print(f"Trials to run: {num_trials}")
        print(f"Delay between trials: {delay_seconds}s")
        print(f"Include validation: {include_validation}")
        print(f"Include implementation: {include_implementation}")
        print(f"{'='*70}")
        
        successful_trials = 0
        failed_trials = 0
        
        for trial_num in range(1, num_trials + 1):
            print(f"\n\n{'*'*60}")
            print(f"TRIAL {trial_num}/{num_trials}")
            print(f"{'*'*60}")
            
            success = self.run_single_trial(
                use_case, sector, demand,
                include_validation, include_implementation
            )
            
            if success:
                successful_trials += 1
                print(f"\n✓ Trial {trial_num} completed successfully")
            else:
                failed_trials += 1
                print(f"\n✗ Trial {trial_num} failed")
            
            # Delay before next trial (except for last trial)
            if trial_num < num_trials and delay_seconds > 0:
                print(f"\nWaiting {delay_seconds} seconds before next trial...")
                time.sleep(delay_seconds)
        
        # Summary
        print(f"\n\n{'='*70}")
        print("SUMMARY")
        print(f"{'='*70}")
        print(f"Total trials: {num_trials}")
        print(f"Successful: {successful_trials}")
        print(f"Failed: {failed_trials}")
        print(f"Success rate: {(successful_trials/num_trials*100):.1f}%")
        
        return successful_trials, failed_trials
    
    def run_batch_variance_trials(self, test_cases: list, trials_per_case: int = 3):
        """Run variance trials for multiple test cases"""
        
        print(f"\n{'='*70}")
        print(f"BATCH VARIANCE TRIAL GENERATION")
        print(f"{'='*70}")
        print(f"Test cases: {len(test_cases)}")
        print(f"Trials per case: {trials_per_case}")
        print(f"Total trials to generate: {len(test_cases) * trials_per_case}")
        print(f"{'='*70}")
        
        overall_successful = 0
        overall_failed = 0
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n\n{'#'*70}")
            print(f"TEST CASE {i}/{len(test_cases)}")
            print(f"{'#'*70}")
            
            successful, failed = self.run_multiple_trials(
                use_case=test_case['use_case'],
                sector=test_case['sector'],
                demand=test_case['demand'],
                num_trials=trials_per_case,
                delay_seconds=3,
                include_validation=test_case.get('include_validation', True),
                include_implementation=test_case.get('include_implementation', True)
            )
            
            overall_successful += successful
            overall_failed += failed
            
            # Longer delay between different test cases
            if i < len(test_cases):
                print(f"\n\nWaiting 10 seconds before next test case...")
                time.sleep(10)
        
        # Final summary
        print(f"\n\n{'='*70}")
        print("FINAL BATCH SUMMARY")
        print(f"{'='*70}")
        print(f"Total test cases: {len(test_cases)}")
        print(f"Total trials attempted: {len(test_cases) * trials_per_case}")
        print(f"Total successful: {overall_successful}")
        print(f"Total failed: {overall_failed}")
        print(f"Overall success rate: {(overall_successful/(overall_successful+overall_failed)*100):.1f}%")
        
        return overall_successful, overall_failed


def main():
    parser = argparse.ArgumentParser(description='Generate variance trials for LLM output analysis')
    
    parser.add_argument('--use-case', type=str, help='Use case for the trial')
    parser.add_argument('--sector', type=str, help='Sector for the trial')
    parser.add_argument('--demand', type=str, help='Demand for the trial')
    parser.add_argument('--trials', type=int, default=5, help='Number of trials to run (default: 5)')
    parser.add_argument('--delay', type=int, default=5, help='Delay between trials in seconds (default: 5)')
    parser.add_argument('--no-validation', action='store_true', help='Skip validation phase')
    parser.add_argument('--no-implementation', action='store_true', help='Skip implementation phase')
    parser.add_argument('--batch', action='store_true', help='Run batch mode with predefined test cases')
    
    args = parser.parse_args()
    
    generator = VarianceTrialGenerator()
    
    if args.batch:
        # Predefined test cases for batch mode
        test_cases = [
            {
                'use_case': 'People mover mobility',
                'sector': 'RoboTaxi',
                'demand': 'navigation optimization',
                'include_validation': True,
                'include_implementation': True
            },
            {
                'use_case': 'Delivery bots mobility',
                'sector': 'Micro Mobility',
                'demand': 'last-mile efficiency',
                'include_validation': True,
                'include_implementation': True
            },
            {
                'use_case': 'Hub to Hub mobility',
                'sector': 'Autonomous Mega Trucks',
                'demand': 'fuel efficiency',
                'include_validation': False,  # Skip validation for faster processing
                'include_implementation': True
            },
            {
                'use_case': 'Railway mobility',
                'sector': 'Automated Metros & Trains',
                'demand': 'predictive maintenance',
                'include_validation': True,
                'include_implementation': False  # Skip implementation
            },
            {
                'use_case': 'Air mobility',
                'sector': 'Drones',
                'demand': 'autonomous flight control',
                'include_validation': True,
                'include_implementation': True
            }
        ]
        
        generator.run_batch_variance_trials(test_cases, trials_per_case=args.trials)
        
    elif args.use_case and args.sector and args.demand:
        # Single test case mode
        generator.run_multiple_trials(
            use_case=args.use_case,
            sector=args.sector,
            demand=args.demand,
            num_trials=args.trials,
            delay_seconds=args.delay,
            include_validation=not args.no_validation,
            include_implementation=not args.no_implementation
        )
    else:
        print("Error: Please provide either --batch flag or all of --use-case, --sector, and --demand")
        parser.print_help()


if __name__ == "__main__":
    main()