# setup_assessment.py

import os
import json
from pathlib import Path

def setup_assessment_framework():
    """Setup the assessment framework with necessary files and configurations"""
    
    print("Setting up LLM Quality Assessment Framework...")
    
    # Create directory structure
    directories = [
        'assessments',
        'assessments/reports',
        'assessments/baselines',
        'assessments/evaluations',
        'logs'
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✓ Created directory: {directory}")
    
    # Create default configuration
    config = {
        "assessment": {
            "default_trials": 5,
            "trial_delay_seconds": 2,
            "max_retries": 3
        },
        "thresholds": {
            "diversity": {
                "min_acceptable": 0.5,
                "target": 0.7
            },
            "compliance": {
                "min_acceptable": 0.8,
                "target": 0.95
            },
            "performance": {
                "max_latency_ms": 30000,
                "max_tokens": 3000
            }
        },
        "cost_estimation": {
            "gpt_3_5_per_1k_tokens": 0.002,
            "gpt_4_per_1k_tokens": 0.03
        },
        "database": {
            "assessment_retention_days": 90
        }
    }
    
    with open('assessments/config.json', 'w') as f:
        json.dump(config, f, indent=2)
    print("✓ Created configuration file: assessments/config.json")
    
    # Create sample test cases
    test_cases = [
        {
            "name": "Urban Mobility",
            "use_case": "People mover mobility",
            "sector": "RoboTaxi",
            "demand": "navigation"
        },
        {
            "name": "Logistics",
            "use_case": "Cargo transportation",
            "sector": "Autonomous trucks",
            "demand": "efficiency"
        },
        {
            "name": "Last Mile",
            "use_case": "Last-mile delivery",
            "sector": "Delivery robots",
            "demand": "reliability"
        },
        {
            "name": "Public Transport",
            "use_case": "Mass transit",
            "sector": "Autonomous buses",
            "demand": "safety"
        }
    ]
    
    with open('assessments/test_cases.json', 'w') as f:
        json.dump(test_cases, f, indent=2)
    print("✓ Created test cases file: assessments/test_cases.json")
    
    # Create assessment schedule
    schedule = {
        "daily_regression": {
            "enabled": True,
            "time": "02:00",
            "test_cases": ["Urban Mobility", "Logistics"],
            "trials_per_case": 3
        },
        "weekly_comprehensive": {
            "enabled": True,
            "day": "Sunday",
            "time": "03:00",
            "test_cases": "all",
            "trials_per_case": 5
        },
        "monthly_baseline_update": {
            "enabled": True,
            "day": 1,
            "time": "04:00"
        }
    }
    
    with open('assessments/schedule.json', 'w') as f:
        json.dump(schedule, f, indent=2)
    print("✓ Created schedule file: assessments/schedule.json")
