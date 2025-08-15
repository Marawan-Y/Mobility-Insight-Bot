# human_evaluation.py

import random
import json
from datetime import datetime
from typing import List, Dict

class HumanEvaluator:
    """Human-in-the-loop evaluation system"""
    
    def __init__(self):
        self.evaluation_queue = []
        self.completed_evaluations = []
    
    def create_evaluation_task(
        self,
        trial_results: List,
        sample_size: int = 5
    ) -> Dict:
        """Create human evaluation tasks from trial results"""
        
        # Sample random outputs for evaluation
        samples = random.sample(trial_results, min(sample_size, len(trial_results)))
        
        evaluation_task = {
            'task_id': datetime.now().strftime('%Y%m%d_%H%M%S'),
            'created': datetime.now().isoformat(),
            'samples': []
        }
        
        for i, result in enumerate(samples):
            sample = {
                'sample_id': f"{evaluation_task['task_id']}_{i+1}",
                'input': {
                    'use_case': result.input.use_case,
                    'sector': result.input.sector,
                    'demand': result.input.demand
                },
                'output': {
                    'trend_titles': result.trend_titles,
                    'snippet': result.raw_output[:500] + '...'
                },
                'metrics': {
                    'latency_ms': result.latency_ms,
                    'token_count': result.token_count
                }
            }
            evaluation_task['samples'].append(sample)
        
        # Save to evaluation queue
        self.evaluation_queue.append(evaluation_task)
        
        # Generate evaluation form
        self.generate_evaluation_form(evaluation_task)
        
        return evaluation_task
    
    def generate_evaluation_form(self, task: Dict):
        """Generate HTML evaluation form"""
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>LLM Output Evaluation - {task['task_id']}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .sample {{ border: 1px solid #ddd; padding: 20px; margin: 20px 0; }}
        .rating {{ margin: 10px 0; }}
        input[type="range"] {{ width: 300px; }}
        .submit-btn {{ background: #007bff; color: white; padding: 10px 20px; }}
    </style>
</head>
<body>
    <h1>LLM Output Quality Evaluation</h1>
    <p>Please evaluate the following outputs for quality and relevance.</p>
    
    <form id="evaluationForm">
"""
        
        for sample in task['samples']:
            html += f"""
        <div class="sample">
            <h3>Sample {sample['sample_id']}</h3>
            <p><strong>Input:</strong></p>
            <ul>
                <li>Use Case: {sample['input']['use_case']}</li>
                <li>Sector: {sample['input']['sector']}</li>
                <li>Demand: {sample['input']['demand']}</li>
            </ul>
            
            <p><strong>Generated Trends:</strong></p>
            <ol>
                {''.join(f"<li>{title}</li>" for title in sample['output']['trend_titles'])}
            </ol>
            
            <div class="rating">
                <label>Relevance (1-10): 
                    <input type="range" name="{sample['sample_id']}_relevance" 
                           min="1" max="10" value="5">
                    <span class="value">5</span>
                </label>
            </div>
            
            <div class="rating">
                <label>Innovation (1-10): 
                    <input type="range" name="{sample['sample_id']}_innovation" 
                           min="1" max="10" value="5">
                    <span class="value">5</span>
                </label>
            </div>
            
            <div class="rating">
                <label>Practicality (1-10): 
                    <input type="range" name="{sample['sample_id']}_practicality" 
                           min="1" max="10" value="5">
                    <span class="value">5</span>
                </label>
            </div>
            
            <div class="rating">
                <label>Overall Quality (1-10): 
                    <input type="range" name="{sample['sample_id']}_overall" 
                           min="1" max="10" value="5">
                    <span class="value">5</span>
                </label>
</div>
           
           <div>
               <label>Comments:
                   <textarea name="{sample['sample_id']}_comments" 
                             rows="3" cols="50"></textarea>
               </label>
           </div>
       </div>
"""
       
       html += """
       <button type="submit" class="submit-btn">Submit Evaluation</button>
   </form>
   
   <script>
       // Update range value displays
       document.querySelectorAll('input[type="range"]').forEach(input => {
           input.addEventListener('input', (e) => {
               e.target.nextElementSibling.textContent = e.target.value;
           });
       });
       
       // Handle form submission
       document.getElementById('evaluationForm').addEventListener('submit', (e) => {
           e.preventDefault();
           
           const formData = new FormData(e.target);
           const evaluation = {
               task_id: '""" + task['task_id'] + """',
               timestamp: new Date().toISOString(),
               ratings: {}
           };
           
           for (let [key, value] of formData.entries()) {
               evaluation.ratings[key] = value;
           }
           
           // Send to server or save locally
           console.log('Evaluation submitted:', evaluation);
           alert('Thank you for your evaluation!');
           
           // Save to localStorage for demo
           localStorage.setItem('evaluation_' + evaluation.task_id, JSON.stringify(evaluation));
       });
   </script>
</body>
</html>
"""
       
       # Save evaluation form
       filename = f"evaluation_form_{task['task_id']}.html"
       with open(filename, 'w') as f:
           f.write(html)
       
       print(f"✓ Evaluation form saved to: {filename}")
   
   def process_evaluation_results(self, evaluation_file: str) -> Dict:
       """Process completed human evaluations"""
       
       with open(evaluation_file, 'r') as f:
           evaluations = json.load(f)
       
       # Aggregate results
       results = {
           'task_id': evaluations['task_id'],
           'num_evaluators': len(evaluations['responses']),
           'metrics': {
               'relevance': [],
               'innovation': [],
               'practicality': [],
               'overall': []
           },
           'comments': []
       }
       
       # Process each evaluator's response
       for response in evaluations['responses']:
           for rating_key, rating_value in response['ratings'].items():
               if '_relevance' in rating_key:
                   results['metrics']['relevance'].append(float(rating_value))
               elif '_innovation' in rating_key:
                   results['metrics']['innovation'].append(float(rating_value))
               elif '_practicality' in rating_key:
                   results['metrics']['practicality'].append(float(rating_value))
               elif '_overall' in rating_key:
                   results['metrics']['overall'].append(float(rating_value))
               elif '_comments' in rating_key and rating_value:
                   results['comments'].append(rating_value)
       
       # Calculate statistics
       import numpy as np
       
       summary = {
           'task_id': results['task_id'],
           'num_evaluators': results['num_evaluators'],
           'average_scores': {},
           'score_distribution': {},
           'inter_rater_reliability': {}
       }
       
       for metric, scores in results['metrics'].items():
           if scores:
               summary['average_scores'][metric] = {
                   'mean': np.mean(scores),
                   'std': np.std(scores),
                   'min': np.min(scores),
                   'max': np.max(scores)
               }
               
               # Calculate inter-rater reliability (simplified)
               if len(scores) > 1:
                   summary['inter_rater_reliability'][metric] = 1 - (np.std(scores) / 4.5)  # Normalized
       
       summary['comments'] = results['comments']
       
       return summary

# Example usage for human evaluation integration
if __name__ == "__main__":
   from llm_quality_assessment import LLMQualityAssessor, TrialInput
   from Final_Structured_app import generate_trends
   
   # Run some trials
   assessor = LLMQualityAssessor()
   trial_input = TrialInput(
       use_case="People mover mobility",
       sector="RoboTaxi",
       demand="navigation"
   )
   
   # Collect trial results
   results = []
   for i in range(5):
       result = assessor.run_trial(trial_input, generate_trends)
       results.append(result)
   
   # Create human evaluation task
   evaluator = HumanEvaluator()
   evaluation_task = evaluator.create_evaluation_task(results, sample_size=3)
   
   print(f"✓ Created evaluation task: {evaluation_task['task_id']}")
   print("Please complete the evaluation form and process results.")