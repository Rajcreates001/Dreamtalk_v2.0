# Adapted from Chatbot-Memory (MIT License)
from dotenv import load_dotenv
import os
from .chatbot import ChatBot
from .personality_manager import PersonalityManager
from .relationship_manager import RelationshipManager
import json
import shutil
from .autonomous_chat import AutonomousChat

def remove_user_relationship_dynamics():
    personality_manager = PersonalityManager()
    users_dir = os.path.join(personality_manager.base_dir, "users")
    
    if not os.path.exists(users_dir):
        return
        
    for user_name in os.listdir(users_dir):
        user_dir = os.path.join(users_dir, user_name)
        if os.path.isdir(user_dir):
            social_dynamics_file = os.path.join(user_dir, "social-dynamics.json")
            if os.path.exists(social_dynamics_file):
                os.remove(social_dynamics_file)
                print(f"Removed social-dynamics.json from {user_name}")
            
            core_identity_file = os.path.join(user_dir, "core-identity.json")
            if os.path.exists(core_identity_file):
                os.remove(core_identity_file)
                print(f"Removed core-identity.json from {user_name}")
            
            relationships_dir = os.path.join(user_dir, "relationships")
            if os.path.exists(relationships_dir):
                shutil.rmtree(relationships_dir)
                print(f"Removed relationships directory from {user_name}")

def cleanup_workspace():
    personality_manager = PersonalityManager()
    base_dir = personality_manager.base_dir
    
    os.makedirs(os.path.join(base_dir, "ai"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, "users"), exist_ok=True)
    
    remove_user_relationship_dynamics()
    
    ai_relationships_dir = os.path.join(base_dir, "ai", "relationships")
    if os.path.exists(ai_relationships_dir):
        shutil.rmtree(ai_relationships_dir)
        print("Removed relationships directory from ai directory")
    
    for item in os.listdir(base_dir):
        if item not in ["ai", "users"]:
            item_path = os.path.join(base_dir, item)
            if os.path.isdir(item_path):
                if os.path.exists(os.path.join(item_path, "is_user")):
                    target_path = os.path.join(base_dir, "users", item)
                    if not os.path.exists(target_path):
                        shutil.move(item_path, target_path)
                        print(f"Moved user personality {item} to users directory")
                else:
                    target_path = os.path.join(base_dir, "ai", item)
                    if not os.path.exists(target_path):
                        shutil.move(item_path, target_path)
                        print(f"Moved AI personality {item} to ai directory")
    
    ai_dir = os.path.join(base_dir, "ai")
    for ai_name in os.listdir(ai_dir):
        ai_path = os.path.join(ai_dir, ai_name)
        if os.path.isdir(ai_path):
            relationships_dir = os.path.join(ai_path, "relationships")
            if not os.path.exists(relationships_dir):
                os.makedirs(relationships_dir)
                print(f"Created relationships directory for {ai_name}")
            
            relationship_manager = RelationshipManager(ai_path)
            
            for other_ai in os.listdir(ai_dir):
                if other_ai != ai_name:
                    relationship_file = relationship_manager.get_relationship_file(other_ai)
                    if not os.path.exists(relationship_file):
                        relationship_manager.save_relationship(other_ai, relationship_manager._create_blank_relationship(other_ai))
            
            users_dir = os.path.join(base_dir, "users")
            for user_name in os.listdir(users_dir):
                relationship_file = relationship_manager.get_relationship_file(user_name)
                if not os.path.exists(relationship_file):
                    relationship_manager.save_relationship(user_name, relationship_manager._create_blank_relationship(user_name))

def setup_api_key():
    load_dotenv()
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("\nOpenAI API key not found in environment variables.")
        print("You can get your API key from: https://platform.openai.com/api-keys")
        print("Please enter your OpenAI API key:")
        api_key = input("> ").strip()
        os.environ['OPENAI_API_KEY'] = api_key
        
        save = input("\nWould you like to save this API key to .env file? (y/n): ").lower()
        if save == 'y':
            with open(".env", "a") as f:
                f.write(f"\nOPENAI_API_KEY={api_key}\n")
            print("API key saved to .env file!")

def migrate_existing_personalities():
    personality_manager = PersonalityManager()
    old_dir = personality_manager.base_dir
    ai_dir = os.path.join(old_dir, "ai")
    users_dir = os.path.join(old_dir, "users")
    
    os.makedirs(ai_dir, exist_ok=True)
    os.makedirs(users_dir, exist_ok=True)
    
    if os.path.exists(old_dir):
        for item in os.listdir(old_dir):
            if item not in ["ai", "users"]:
                item_path = os.path.join(old_dir, item)
                if os.path.isdir(item_path):
                    if os.path.exists(os.path.join(item_path, "is_user")):
                        shutil.move(item_path, os.path.join(users_dir, item))
                    else:
                        shutil.move(item_path, os.path.join(ai_dir, item))

def check_existing_user(name):
    personality_manager = PersonalityManager()
    users_dir = os.path.join(personality_manager.base_dir, "users", name)
    
    if os.path.exists(users_dir):
        return True
    return False

def get_available_personalities():
    personality_manager = PersonalityManager()
    ai_dir = os.path.join(personality_manager.base_dir, "ai")
    personalities = []
    
    if os.path.exists(ai_dir):
        personalities = [d for d in os.listdir(ai_dir) 
                        if os.path.isdir(os.path.join(ai_dir, d))]
    
    return personalities

def setup_relationships(personalities):
    personality_manager = PersonalityManager()
    relationship_manager = RelationshipManager(personality_manager.base_dir)
    
    relationship_data = {
        "previous_interactions": [],
        "observed_traits": [],
        "trust_level": 0.5,
        "relationship_status": "acquaintance"
    }
    
    for person1 in personalities:
        for person2 in personalities:
            if person1 != person2:
                rel_dir = os.path.join(personality_manager.base_dir, "ai", person1, "relationships", person2)
                if not os.path.exists(rel_dir):
                    os.makedirs(rel_dir)
                    relationship_manager.save_relationship(person1, relationship_data)
                    relationship_manager.save_relationship(person2, relationship_data)
                    print(f"Created {person1}-{person2} relationship")

def create_user_personality(name):
    personality_manager = PersonalityManager()
    user_dir = os.path.join(personality_manager.base_dir, "users", name)
    
    if os.path.exists(user_dir):
        print(f"\nLoading existing personality for {name}")
        return True
    
    os.makedirs(user_dir)
    
    with open(os.path.join(user_dir, "is_user"), "w") as f:
        f.write("")
        
    print(f"\nCreated new personality for {name}")
    return True

def select_personality(personalities, prompt):
    while True:
        print(f"\n{prompt}")
        for i, name in enumerate(personalities, 1):
            print(f"{i}. {name}")
        
        try:
            choice = int(input("\nEnter your choice (number): "))
            if 1 <= choice <= len(personalities):
                return personalities[choice - 1]
            print("Invalid choice. Please try again.")
        except ValueError:
            print("Please enter a valid number.")

def main():
    try:
        cleanup_workspace()
        
        personalities = get_available_personalities()
        
        if not personalities:
            print("No AI personalities found in my-personality/ai directory.")
            print("Please add AI personality directories to my-personality/ai/")
            print("Each AI personality should be in its own directory with the following structure:")
            print("my-personality/ai/<personality_name>/")
            print("  core-identity.json")
            print("  interests-values.json")
            print("  emotional-framework.json")
            return
        
        print("\nWelcome to the AI Chat System!")
        print("\n1. Chat with an AI personality")
        print("2. Watch autonomous conversation")
        
        choice = input("\nEnter your choice (1 or 2): ")
        
        if choice == "1":
            while True:
                user_name = input("\nEnter your name: ").strip()
                if create_user_personality(user_name):
                    break
            
            user_bot = ChatBot(user_name, is_user=True)
            
            print("\nAvailable AI personalities to chat with:")
            ai_personality = select_personality(personalities, "Select who you want to chat with:")
            
            ai_bot = ChatBot(ai_personality)
            
            print(f"\nStarting chat between {user_name} and {ai_personality}...")
            print("Type 'quit' to end the conversation.")
            
            while True:
                user_message = input(f"\n{user_name}: ").strip()
                if user_message.lower() == 'quit':
                    break
                    
                ai_response = ai_bot.get_response(user_message, user_name)
                print(f"\n{ai_personality}: {ai_response}")
                
                ai_bot.relationship_manager.update_relationship(
                    user_name,
                    [{"speaker": user_name, "message": user_message},
                     {"speaker": ai_personality, "message": ai_response}]
                )
        
        elif choice == "2":
            print("\nAvailable AI personalities:")
            personality1 = select_personality(personalities, "Select first personality:")
            personality2 = select_personality(personalities, "Select second personality:")
            
            if personality1 == personality2:
                print("Please select two different personalities.")
                return
            
            bot1 = ChatBot(personality1)
            bot2 = ChatBot(personality2)
            
            autonomous_chat = AutonomousChat()
            autonomous_chat.start_conversation(bot1, bot2)
            
        else:
            print("Invalid choice. Please enter 1 or 2.")
            
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
