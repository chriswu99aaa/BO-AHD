"""
Parallel action executor for Bayesian Optimization.
This module provides parallel execution of action generation tasks with retry logic.
"""

import concurrent.futures
import threading
from typing import List, Optional, Tuple, NamedTuple, Dict, Any
import numpy as np
import logging
import traceback
from dataclasses import dataclass
from enum import Enum


class GenerationStatus(Enum):
    """Status of action generation."""
    PENDING = "pending"
    GENERATING = "generating" 
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class GenerationResult:
    """Result of a single action generation attempt."""
    success: bool
    action: str
    code: Optional[str] = None
    algorithm: Optional[str] = None
    feature_vector: Optional[np.ndarray] = None
    error: Optional[str] = None
    attempts: int = 0


class ParallelActionExecutor:
    """
    Executes action generation tasks in parallel using a thread pool.
    
    This class manages concurrent generation of heuristic actions with retry logic
    and proper synchronization.
    """
    
    def __init__(self, bo_interface, max_workers: int = 6, timeout_per_action: int = 300):
        """
        Initialize the parallel executor.
        
        Args:
            bo_interface: The BOInterface instance for generating heuristics
            max_workers: Maximum number of worker threads (default: 6 for 6 action types)
            timeout_per_action: Timeout in seconds for each action generation
        """
        self.bo_interface = bo_interface
        self.max_workers = max_workers
        self.timeout_per_action = timeout_per_action
        self.executor = None
        self._lock = threading.Lock()
        self._logger = logging.getLogger(__name__)
        
    def __enter__(self):
        """Context manager entry."""
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - shutdown executor."""
        self.shutdown()
        
    def execute_actions(self, actions: List[str], parent_node, max_retries: int = 5) -> List[GenerationResult]:
        """
        Execute multiple action generation tasks in parallel.
        
        Args:
            actions: List of action types to generate (e.g., ['e1', 'e2', 'm1', 'm2', 's1'])
            parent_node: The parent HeuristicNode for context
            max_retries: Maximum number of retry attempts per action
            
        Returns:
            List of GenerationResult objects for each action
        """
        if self.executor is None:
            self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers)
            
        self._logger.info(f"Starting parallel execution of {len(actions)} actions with max_retries={max_retries}")
        
        # Submit all tasks to the executor
        future_to_action = {}
        for action in actions:
            if action == 'i1':
                # i1 is only for initialization, skip in expansion
                continue
                
            future = self.executor.submit(
                self._execute_single_action,
                action, parent_node, max_retries
            )
            future_to_action[future] = action
            
        # Collect results as they complete
        results = []
        for future in concurrent.futures.as_completed(future_to_action, timeout=self.timeout_per_action * len(actions)):
            action = future_to_action[future]
            try:
                result = future.result(timeout=self.timeout_per_action)
                results.append(result)
                self._logger.info(f"Action {action} completed: success={result.success}, attempts={result.attempts}")
            except concurrent.futures.TimeoutError:
                self._logger.warning(f"Action {action} timed out after {self.timeout_per_action} seconds")
                results.append(GenerationResult(
                    success=False,
                    action=action,
                    error=f"Timeout after {self.timeout_per_action} seconds",
                    attempts=max_retries
                ))
            except Exception as e:
                self._logger.error(f"Action {action} failed with exception: {e}")
                results.append(GenerationResult(
                    success=False,
                    action=action,
                    error=str(e),
                    attempts=max_retries
                ))
                
        return results
    
    def _execute_single_action(self, action: str, parent_node, max_retries: int) -> GenerationResult:
        """
        Execute a single action generation with retry logic.
        
        Args:
            action: Action type to generate
            parent_node: Parent HeuristicNode for context
            max_retries: Maximum retry attempts
            
        Returns:
            GenerationResult with success status and generated data
        """
        attempts = 0
        last_error = None
        
        for attempt in range(max_retries):
            attempts = attempt + 1
            try:
                self._logger.debug(f"Attempt {attempts}/{max_retries} for action {action}")
                
                # Generate heuristic code
                code, algorithm = self.bo_interface.generate_heuristic_by_action(action)
                
                # Check for duplicate code (simplified - actual duplicate check needs population context)
                # This is handled in the BayesianOptimizer_Local class
                
                # Create feature vector (would need embed_code method from parent)
                # This is handled in the BayesianOptimizer_Local class
                
                # Return successful result
                return GenerationResult(
                    success=True,
                    action=action,
                    code=code,
                    algorithm=algorithm,
                    attempts=attempts
                )
                
            except Exception as e:
                last_error = str(e)
                self._logger.warning(f"Attempt {attempts}/{max_retries} failed for action {action}: {last_error}")
                
                # Log traceback for debugging
                if attempt == max_retries - 1:
                    self._logger.debug(f"Traceback for action {action}:\n{traceback.format_exc()}")
                    
                # Exponential backoff before retry (except on last attempt)
                if attempt < max_retries - 1:
                    wait_time = min(2 ** attempt, 10)  # Exponential backoff, max 10 seconds
                    import time
                    time.sleep(wait_time)
        
        # All retries failed
        return GenerationResult(
            success=False,
            action=action,
            error=last_error or "All retry attempts failed",
            attempts=attempts
        )
    
    def shutdown(self):
        """Shutdown the thread pool executor."""
        if self.executor:
            self.executor.shutdown(wait=True)
            self.executor = None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the executor."""
        if self.executor:
            return {
                "max_workers": self.max_workers,
                "active_threads": self.executor._max_workers,  # Access protected member
                "timeout_per_action": self.timeout_per_action
            }
        return {"executor": "not_initialized"}