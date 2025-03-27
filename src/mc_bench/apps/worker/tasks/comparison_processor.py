from .elo_calculation import process_comparison_task as process_elo
from .glicko_calculation import process_comparison_task as process_glicko

@app.task(name="comparison_processor.process_comparison")
def process_comparison(comparison_id):
    """Process a single comparison, updating ratings and leaderboards."""
    logger.info(f"Processing comparison {comparison_id}")
    
    # Process for ELO ratings
    process_elo.delay(comparison_id)
    
    # Also process for Glicko-2 ratings
    process_glicko.delay(comparison_id)
    
    return f"Processed comparison {comparison_id}" 