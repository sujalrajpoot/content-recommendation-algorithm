from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
import json
from pathlib import Path

class EngagementScoreError(Exception):
    """Base exception class for engagement score calculation errors."""
    pass

class FileOperationError(EngagementScoreError):
    """Exception raised for errors during file operations."""
    pass

class ValidationError(EngagementScoreError):
    """Exception raised for validation errors in input data."""
    pass

class ActivityType(Enum):
    """Enum representing different types of user engagement activities."""
    LIKE = auto()
    SHARE = auto()
    COMMENT = auto()
    TIME_SPENT = auto()

@dataclass
class ScoringConfig:
    """Configuration class for engagement scoring parameters."""
    max_time: int = 120
    like_score: int = 30
    share_score: int = 10
    comment_score: int = 20
    time_weight: float = 1.5

    @property
    def max_possible_score(self) -> float:
        """Calculate the maximum possible engagement score."""
        return (self.max_time * self.time_weight) + self.like_score + \
               (20 * self.share_score) + self.comment_score

class DataValidator:
    """Validator class for input data validation."""
    
    @staticmethod
    def validate_entry(entry: Dict[str, Any]) -> None:
        """
        Validate a single user entry.
        
        Args:
            entry: Dictionary containing user engagement data.
            
        Raises:
            ValidationError: If entry data is invalid.
            
        Expected data format:
        {
            "time_spent": int or float,
            "liked": bool,
            "shares": int,
            "commented": bool,
            "hashtags": str or list  # Now accepts either string or list
        }
        """
        required_fields = {'time_spent', 'liked', 'shares', 'commented', 'hashtags'}
        if not all(field in entry for field in required_fields):
            raise ValidationError("Missing required fields in entry")
        
        if not isinstance(entry['time_spent'], (int, float)):
            raise ValidationError("time_spent must be numeric")
        
        if not isinstance(entry['shares'], int):
            raise ValidationError("shares must be an integer")
        
        # Convert string hashtag to list if necessary
        if isinstance(entry['hashtags'], str):
            entry['hashtags'] = [entry['hashtags']]
        elif not isinstance(entry['hashtags'], list):
            raise ValidationError("hashtags must be a string or a list")
        
        # Convert boolean fields if they're strings
        if isinstance(entry['liked'], str):
            entry['liked'] = entry['liked'].lower() == 'true'
        if isinstance(entry['commented'], str):
            entry['commented'] = entry['commented'].lower() == 'true'

class EngagementScorer(ABC):
    """Abstract base class for engagement scoring implementations."""
    
    @abstractmethod
    def calculate_score(self, entry: Dict[str, Any]) -> float:
        """Calculate engagement score for a single entry."""
        pass

class StandardEngagementScorer(EngagementScorer):
    """Standard implementation of engagement scoring."""
    
    def __init__(self, config: ScoringConfig):
        """
        Initialize the scorer with configuration.
        
        Args:
            config: ScoringConfig instance containing scoring parameters.
        """
        self.config = config

    def calculate_score(self, entry: Dict[str, Any]) -> float:
        """
        Calculate engagement score for a single entry.
        
        Args:
            entry: Dictionary containing user engagement data.
            
        Returns:
            float: Calculated engagement score as a percentage.
        """
        DataValidator.validate_entry(entry)
        
        raw_score = (
            entry["time_spent"] * self.config.time_weight +
            (self.config.like_score if entry["liked"] else 0) +
            (entry["shares"] * self.config.share_score) +
            (self.config.comment_score if entry["commented"] else 0)
        )
        
        return (raw_score / self.config.max_possible_score) * 100

class EngagementAnalyzer:
    """Main class for analyzing user engagement data."""
    
    def __init__(self, scorer: EngagementScorer):
        """
        Initialize the analyzer with a scorer implementation.
        
        Args:
            scorer: Implementation of EngagementScorer to use for calculations.
        """
        self.scorer = scorer

    def process_user_data(self, data: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        Process user data and calculate top engagement scores.
        
        Args:
            data: Dictionary mapping user IDs to lists of engagement entries.
            
        Returns:
            List[Dict[str, Any]]: List of user results with top two scores.
        """
        user_top_scores = []
        
        for user_id, entries in data.items():
            processed_entries = []
            for entry in entries:
                try:
                    score = self.scorer.calculate_score(entry)
                    processed_entries.append({**entry, "engagement_score": score})
                except ValidationError as e:
                    print(f"Skipping invalid entry for user {user_id}: {str(e)}")
                    continue
            
            sorted_entries = sorted(
                processed_entries,
                key=lambda x: x["engagement_score"],
                reverse=True
            )
            top_two_entries = sorted_entries[:2]
            
            if top_two_entries:  # Only add users with valid entries
                user_top_scores.append({
                    "user_id": user_id,
                    "hashtags": [entry["hashtags"] for entry in top_two_entries],
                    "engagement_score": [
                        round(entry["engagement_score"], 2)
                        for entry in top_two_entries
                    ]
                })
        
        return user_top_scores

def process_engagement_data(
    input_path: str,
    output_path: str,
    config: Optional[ScoringConfig] = None
) -> None:
    """
    Main function to process engagement data from input file and write results.
    
    Args:
        input_path: Path to input JSON file.
        output_path: Path to output JSON file.
        config: Optional ScoringConfig instance. Uses default if None.
        
    Raises:
        FileOperationError: If file operations fail.
    """
    if config is None:
        config = ScoringConfig()
    
    try:
        input_path = Path(input_path)
        output_path = Path(output_path)
        
        with input_path.open('r') as file:
            data = json.load(file)
        
        analyzer = EngagementAnalyzer(StandardEngagementScorer(config))
        results = analyzer.process_user_data(data)
        
        with output_path.open('w') as f:
            json.dump(results, f, indent=4)
            
        print("Successfully processed engagement data and wrote results.")
            
    except (json.JSONDecodeError, OSError) as e:
        raise FileOperationError(f"Error processing files: {str(e)}")

if __name__ == "__main__":
    # Example of expected input data format
    example_data = {
        "user_123": [
            {
                "time_spent": 60,
                "liked": True,
                "shares": 5,
                "commented": True,
                "hashtags": ["python", "coding"]  # Can be list
            },
            {
                "time_spent": 45,
                "liked": False,
                "shares": 2,
                "commented": True,
                "hashtags": "javascript"  # Or single string
            }
        ]
    }
    
    INPUT_FILE_PATH = "./user_data.json"
    OUTPUT_FILE_PATH = "./top_user_scores.json"
    
    try:
        process_engagement_data(INPUT_FILE_PATH, OUTPUT_FILE_PATH)
    except EngagementScoreError as e:
        print(f"Error: {str(e)}")
        exit(1)
