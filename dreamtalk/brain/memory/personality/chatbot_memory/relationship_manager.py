# Adapted from Chatbot-Memory (MIT License)
import os
import json
import time
from typing import Dict, List, Optional
from openai import OpenAI
from dotenv import load_dotenv

class RelationshipManager:
    def __init__(self, personality_dir: str):
        self.personality_dir = personality_dir
        self.relationships_dir = os.path.join(self.personality_dir, "relationships")
        if not os.path.exists(self.relationships_dir):
            os.makedirs(self.relationships_dir)
        self.current_relationships = {}
        
        self.name = os.path.basename(self.personality_dir)
        
        load_dotenv()
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OpenAI API key not found in environment variables or .env file")
        self.client = OpenAI(api_key=api_key)

    def get_relationship_file(self, other_name: str) -> str:
        return os.path.join(self.relationships_dir, f"{other_name}.json")

    def load_relationship(self, other_name: str) -> Dict:
        file_path = self.get_relationship_file(other_name)
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return json.load(f)
        return self._create_blank_relationship(other_name)

    def _create_blank_relationship(self, other_name: str) -> Dict:
        return {
            "interactions": [],
            "observed_traits": [],
            "shared_experiences": [],
            "emotional_dynamics": {
                "positive_moments": [],
                "challenges": [],
                "trust_level": "neutral"
            },
            "communication_patterns": {
                "topics": [],
                "style": [],
                "frequency": "occasional"
            },
            "relationship_development": {
                "milestones": [],
                "current_status": "acquaintance",
                "growth_areas": []
            },
            "social_preferences": {
                "preferred_topics": [],
                "interaction_style": [],
                "boundaries": []
            },
            "interaction_history": {
                "recent_interactions": [],
                "key_moments": [],
                "conflicts": [],
                "resolutions": []
            }
        }

    def save_relationship(self, other_name: str, data: Dict) -> None:
        file_path = self.get_relationship_file(other_name)
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)

    def _summarize_relationship(self, data: Dict) -> str:
        system_prompt = f"""You are a relationship summarizer. Create a detailed summary of the relationship between {self.name} and the user.

The summary should include:
1. Key shared experiences and memories
2. Important conversations and topics discussed
3. Emotional dynamics and trust level
4. Communication patterns and preferences
5. Relationship milestones and current status
6. Notable interactions and their impact
7. Any significant challenges or positive moments

Format the summary as a natural narrative that captures the essence of the relationship. Include specific details and examples from the interaction history.

Make the summary detailed enough to preserve important memories and context, but concise enough to be useful for future interactions."""
        
        summary_data = {
            "interactions": data.get("interactions", []),
            "shared_experiences": data.get("shared_experiences", []),
            "emotional_dynamics": data.get("emotional_dynamics", {}),
            "communication_patterns": data.get("communication_patterns", {}),
            "relationship_development": data.get("relationship_development", {}),
            "interaction_history": data.get("interaction_history", {})
        }
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Summarize this relationship data:\n\n{json.dumps(summary_data, indent=2)}"}
        ]
        
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=500,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()

    def update_relationship(self, other_name: str, conversation: List[Dict]) -> None:
        try:
            relationship_data = self.load_relationship(other_name)
            
            file_path = self.get_relationship_file(other_name)
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    lines = f.readlines()
                    if len(lines) > 200:
                        summary = self._summarize_relationship(relationship_data)
                        
                        if "summaries" not in relationship_data:
                            relationship_data["summaries"] = []
                        relationship_data["summaries"].append({
                            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "summary": summary
                        })
                        
                        if len(relationship_data["summaries"]) > 5:
                            relationship_data["summaries"] = relationship_data["summaries"][-5:]
                        
                        relationship_data = {
                            "summaries": relationship_data["summaries"],
                            "interactions": [],
                            "observed_traits": [],
                            "shared_experiences": [],
                            "emotional_dynamics": {
                                "positive_moments": [],
                                "challenges": [],
                                "trust_level": "neutral"
                            },
                            "communication_patterns": {
                                "topics": [],
                                "style": [],
                                "frequency": "occasional"
                            },
                            "relationship_development": {
                                "milestones": [],
                                "current_status": "stranger",
                                "growth_areas": []
                            },
                            "social_preferences": {
                                "preferred_topics": [],
                                "interaction_style": [],
                                "boundaries": []
                            },
                            "interaction_history": {
                                "recent_interactions": [],
                                "key_moments": [],
                                "conflicts": [],
                                "resolutions": []
                            }
                        }
                        
                        self.save_relationship(other_name, relationship_data)
            
            system_prompt = f"""You are a relationship analyzer. Your task is to analyze this conversation and return ONLY a valid JSON object.

IMPORTANT: Your entire response must be a valid JSON object, nothing else.

Analyze the conversation between {self.name} and {other_name} and update their relationship data.

Consider the following relationship context:
{relationship_data.get('summaries', [{}])[-1].get('summary', 'No previous summary available')}

Return format must be exactly:
{{
    "interactions": ["new interaction 1", "new interaction 2"],
    "observed_traits": ["trait 1", "trait 2"],
    "shared_experiences": ["experience 1", "experience 2"],
    "emotional_dynamics": {{
        "positive_moments": ["moment 1", "moment 2"],
        "challenges": ["challenge 1", "challenge 2"],
        "trust_level": "neutral|low|medium|high"
    }},
    "communication_patterns": {{
        "topics": ["topic 1", "topic 2"],
        "style": ["style 1", "style 2"],
        "frequency": "occasional|regular|frequent"
    }},
    "relationship_development": {{
        "milestones": ["milestone 1", "milestone 2"],
        "current_status": "stranger|acquaintance|friend|close_friend",
        "growth_areas": ["area 1", "area 2"]
    }},
    "social_preferences": {{
        "preferred_topics": ["topic 1", "topic 2"],
        "interaction_style": ["style 1", "style 2"],
        "boundaries": ["boundary 1", "boundary 2"]
    }},
    "interaction_history": {{
        "recent_interactions": ["interaction 1", "interaction 2"],
        "key_moments": ["moment 1", "moment 2"],
        "conflicts": ["conflict 1", "conflict 2"],
        "resolutions": ["resolution 1", "resolution 2"]
    }}
}}

Only include fields that need updates. Ensure the response is valid JSON."""
            
            conversation_text = "\n".join([
                f"{msg['speaker']}: {msg['message']}" 
                for msg in conversation
            ])
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Analyze this conversation:\n\n{conversation_text}"}
            ]
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=1000,
                temperature=0.7
            )
            
            response_content = response.choices[0].message.content
            
            try:
                updates = json.loads(response_content)
                merged_data = self._merge_relationship_data(relationship_data, updates)
                self.save_relationship(other_name, merged_data)
                
            except json.JSONDecodeError as e:
                print(f"Error parsing GPT response as JSON: {e}")
                print("Raw response was:", response_content)
        
        except Exception as e:
            print(f"Error in relationship update process: {e}")

    def _merge_relationship_data(self, current_data: Dict, new_data: Dict) -> Dict:
        for key, value in new_data.items():
            if isinstance(value, dict):
                if key not in current_data:
                    current_data[key] = {}
                current_data[key] = self._merge_relationship_data(current_data[key], value)
            elif isinstance(value, list):
                if key not in current_data:
                    current_data[key] = []
                current_data[key].extend(item for item in value if item not in current_data[key])
            else:
                current_data[key] = value
        return current_data
