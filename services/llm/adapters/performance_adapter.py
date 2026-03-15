"""
Performance analysis adapter
Specialized adapter for code performance analysis
"""

import json
import re
from typing import List

import structlog

from adapters.base_adapter import BaseAdapter

logger = structlog.get_logger()


class PerformanceAdapter(BaseAdapter):
    """Adapter for performance analysis tasks"""

    SYSTEM_PROMPT = """You are a performance optimization expert analyzing code.
Your task is to identify performance bottlenecks and suggest optimizations.
Focus on algorithmic complexity, resource usage, and best practices."""

    async def analyze(self, code: str, language: str) -> dict:
        """Analyze code for performance issues"""
        prompt = f"""Analyze the following {language} code for performance issues:

```{language}
{code}
```

Identify:
1. Algorithmic complexity issues (O(n^2), O(2^n), etc.)
2. Inefficient data structure usage
3. Memory allocation issues
4. I/O bottlenecks
5. Caching opportunities
6. Concurrency possibilities

For each issue provide:
- Location (line numbers)
- Current complexity
- Suggested improvement
- Expected performance gain

Format as JSON:
{{
    "issues": [
        {{
            "type": "issue type",
            "location": "line numbers",
            "severity": "high/medium/low",
            "current_complexity": "O(n)",
            "suggested_complexity": "O(log n)",
            "description": "explanation",
            "optimization": "suggested code"
        }}
    ],
    "overall_score": 0-100,
    "summary": "brief summary"
}}"""

        try:
            response_text = await self.generate_prompt(
                system_prompt=self.SYSTEM_PROMPT,
                user_prompt=prompt,
                max_tokens=2048,
                temperature=0.1,
            )

            # Parse JSON response
            try:
                result = json.loads(response_text)
            except json.JSONDecodeError:
                json_match = re.search(r"```json\n(.*?)\n```", response_text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group(1))
                else:
                    result = {"raw_response": response_text}

            return {
                "text": response_text,
                "structured": result,
                "issues_found": len(result.get("issues", [])),
                "overall_score": result.get("overall_score", 50),
                "confidence": 0.8,
                "model_used": "performance-analyzer",
            }

        except Exception as e:
            logger.error(f"Performance analysis failed: {e}")
            return {
                "text": f"Analysis failed: {e}",
                "structured": {},
                "issues_found": 0,
                "overall_score": 0,
                "confidence": 0,
            }

    async def suggest_optimizations(
        self,
        code: str,
        language: str,
        target_metric: str = "time",  # time, memory, throughput
    ) -> dict:
        """Suggest optimizations for specific metrics"""
        prompt = f"""Optimize the following {language} code for {target_metric}:

```{language}
{code}
```

Provide:
1. Optimized code
2. Explanation of changes
3. Expected improvement percentage
4. Trade-offs (if any)

Format as JSON:
{{
    "optimized_code": "the optimized code",
    "explanation": "detailed explanation",
    "expected_improvement": "e.g., 50% faster",
    "trade_offs": "any trade-offs made"
}}"""

        try:
            response_text = await self.generate_prompt(
                system_prompt=self.SYSTEM_PROMPT,
                user_prompt=prompt,
                max_tokens=2048,
                temperature=0.2,
            )

            try:
                result = json.loads(response_text)
            except json.JSONDecodeError:
                json_match = re.search(r"```json\n(.*?)\n```", response_text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group(1))
                else:
                    result = {"optimized_code": response_text}

            return {
                "optimized_code": result.get("optimized_code", ""),
                "explanation": result.get("explanation", ""),
                "expected_improvement": result.get("expected_improvement", ""),
                "trade_offs": result.get("trade_offs", ""),
            }

        except Exception as e:
            logger.error(f"Optimization suggestion failed: {e}")
            return {
                "optimized_code": "",
                "explanation": f"Failed: {e}",
                "expected_improvement": "",
            }

    async def analyze_complexity(self, code: str, language: str) -> dict:
        """Analyze time and space complexity"""
        prompt = f"""Analyze the time and space complexity of this {language} code:

```{language}
{code}
```

Provide:
1. Time complexity (Big O notation)
2. Space complexity (Big O notation)
3. Best case scenario
4. Worst case scenario
5. Bottleneck identification

Format as JSON:
{{
    "time_complexity": "O(n)",
    "space_complexity": "O(1)",
    "best_case": "description",
    "worst_case": "description",
    "bottlenecks": ["list of bottlenecks"]
}}"""

        response_text = await self.generate_prompt(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=prompt,
            max_tokens=1024,
            temperature=0.1,
        )

        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            result = {"raw_analysis": response_text}

        return result
