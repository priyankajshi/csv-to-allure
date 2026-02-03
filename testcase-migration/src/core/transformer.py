import logging
from typing import Dict, List, Any
from src.config import FIELD_MAPPING, STEP_SEPARATOR, ACTION_EXPECTED_SEPARATOR

class TestCaseTransformer:
    """
    Transforms raw CSV data into Allure TestOps API payloads.
    """
    def __init__(self, project_id: int):
        self.project_id = project_id
        self.logger = logging.getLogger("migration.transformer")

    def parse_steps(self, steps_str: str) -> List[Dict[str, str]]:
        """
        Transforms a single string of steps (from CSV) into the required 
        list of step objects for the Allure TestOps API.
        """
        if not steps_str or not steps_str.strip():
            return []
            
        steps_list = []
        # Split by STEP_SEPARATOR or newline
        import re
        raw_steps = re.split(f"{re.escape(STEP_SEPARATOR)}|\n", steps_str)
        
        for raw_step in raw_steps:
            raw_step = raw_step.strip()
            if not raw_step:
                continue
                
            if ACTION_EXPECTED_SEPARATOR in raw_step:
                try:
                    action, expected = raw_step.split(ACTION_EXPECTED_SEPARATOR, 1)
                    steps_list.append({
                        "name": action.strip(),
                        "expectedResult": expected.strip()
                    })
                except ValueError:
                    self.logger.warning(f"Could not parse step: {raw_step}")
                    steps_list.append({"name": raw_step, "expectedResult": ""})
            else:
                steps_list.append({"name": raw_step, "expectedResult": ""})
                
        return steps_list

    def transform(self, row_data: Dict[str, str]) -> Dict[str, Any]:
        """
        Constructs the final JSON payload for the Allure TestOps API.
        """
        payload = {
            "projectId": self.project_id,
            "steps": [],
            "tags": [],
            "description": ""
        }

        for csv_key, api_key in FIELD_MAPPING.items():
            value = row_data.get(csv_key)
            if not value or not value.strip():
                continue
                
            value = value.strip()
            
            if api_key == "description_preconditions":
                # Prepend preconditions to description
                payload["description"] += f"**Preconditions:**\n{value}\n\n"
            elif api_key == "description_steps":
                steps = self.parse_steps(value)
                payload["steps"] = steps
                # Map steps to scenario for Allure TestOps to recognize them as scenario steps
                payload["scenario"] = {"steps": steps}
            elif api_key == "tags":
                # Filter out empty tags. Support both comma and semicolon separators.
                import re
                tags = [tag.strip() for tag in re.split('[,;]', value) if tag.strip()]
                payload["tags"] = [{"name": tag} for tag in tags]
            elif api_key == "priority":
                payload[api_key] = value.upper()
            else:
                payload[api_key] = value
                
        return payload
