import unittest
from src.core.transformer import TestCaseTransformer

class TestTestCaseTransformer(unittest.TestCase):
    def setUp(self):
        self.transformer = TestCaseTransformer(project_id=100)

    def test_parse_steps_simple(self):
        steps_str = "Step 1 | Step 2"
        expected = [
            {"name": "Step 1", "expectedResult": ""},
            {"name": "Step 2", "expectedResult": ""}
        ]
        result = self.transformer.parse_steps(steps_str)
        self.assertEqual(result, expected)

    def test_parse_steps_with_expected(self):
        steps_str = "Action 1; Expected: Result 1 | Action 2"
        expected = [
            {"name": "Action 1", "expectedResult": "Result 1"},
            {"name": "Action 2", "expectedResult": ""}
        ]
        result = self.transformer.parse_steps(steps_str)
        self.assertEqual(result, expected)

    def test_transform_payload(self):
        row = {
            "ID": "TC-01",
            "Title": "Test Login",
            "Priority": "High",
            "Tags": "smoke, auth",
            "Preconditions": "User exists",
            "Steps": "Login; Expected: Success"
        }
        result = self.transformer.transform(row)
        
        self.assertEqual(result['project']['id'], 100)
        self.assertEqual(result['externalId'], "TC-01")
        self.assertEqual(result['name'], "Test Login")
        self.assertEqual(result['priority'], "HIGH")
        
        self.assertEqual(len(result['tags']), 2)
        self.assertEqual(result['tags'][0]['name'], "smoke")
        
        self.assertIn("**Preconditions:**\nUser exists", result['description'])
        self.assertEqual(len(result['steps']), 1)
        self.assertEqual(result['steps'][0]['expectedResult'], "Success")

if __name__ == '__main__':
    unittest.main()
