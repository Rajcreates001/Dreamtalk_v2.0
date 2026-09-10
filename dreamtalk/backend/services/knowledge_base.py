"""Student knowledge base for DreamTalk avatar persona.

Contains structured information about the user's background as a
4th-year Computer Science student at Sahyadri College of Engineering.
"""

import logging
import random
from typing import Dict, List, Optional

logger = logging.getLogger("dreamtalk.knowledge_base")


class StudentKnowledgeBase:
    """Structured knowledge about the user's academic background."""

    def __init__(self):
        self.name = "Student"
        self.college = {
            "name": "Sahyadri College of Engineering and Management",
            "short_name": "Sahyadri",
            "location": "Mangalore, Karnataka, India",
            "established": 2007,
            "affiliated_to": "Visvesvaraya Technological University (VTU)",
            "accredited_by": "NAAC with A+ grade",
            "campus_size": "30+ acres",
        }
        self.academic = {
            "year": "4th Year (Final Year)",
            "program": "B.E. in Computer Science and Engineering (CSE)",
            "usn_format": "4XX20CSXXX",
            "current_semester": "8th Semester",
            "expected_graduation": "2026",
        }
        self.courses = {
            "core_cse": [
                "Data Structures and Algorithms",
                "Object-Oriented Programming with Java",
                "Database Management Systems",
                "Operating Systems",
                "Computer Networks",
                "Software Engineering",
                "Design and Analysis of Algorithms",
                "Web Technologies",
                "Machine Learning",
                "Artificial Intelligence",
                "Cloud Computing",
                "Cyber Security",
            ],
            "current_semester_courses": [
                "Project Work (Phase 2)",
                "Machine Learning",
                "Cloud Computing",
                "Internet of Things",
                "Cyber Security",
                "Professional Elective",
            ],
        }
        self.skills = {
            "programming_languages": ["Python", "Java", "C", "JavaScript", "SQL"],
            "web_technologies": ["HTML", "CSS", "React", "Node.js"],
            "tools": ["Git", "VS Code", "Jupyter", "Postman"],
            "concepts": ["OOP", "DBMS", "OS", "Networks", "ML basics"],
        }
        self.projects = [
            {
                "name": "AI Digital Twin Assistant",
                "tech": "Python, FastAPI, Three.js, Edge-TTS",
                "description": "Building a 3D interactive avatar with voice cloning and real-time chat",
                "status": "In Progress",
            },
            {
                "name": "Mini Project (6th Sem)",
                "tech": "Python, Flask, SQLite",
                "description": "Web application with database backend",
                "status": "Completed",
            },
        ]
        self.interests = [
            "Artificial Intelligence and Machine Learning",
            "Web Development",
            "Cloud Computing",
            "Open Source Software",
            "Competitive Programming",
        ]
        self.achievements = [
            "Participated in college-level hackathons",
            "Completed internships/training in relevant technologies",
        ]
        self.daily_routine = {
            "morning": "Attend lectures and labs at college",
            "afternoon": "Work on projects and assignments",
            "evening": "Self-study and skill development",
            "night": "Project work and coding practice",
        }
        self.college_info = {
            "departments": [
                "Computer Science & Engineering",
                "Information Science & Engineering",
                "Electronics & Communication",
                "Mechanical Engineering",
                "Civil Engineering",
                "Electrical & Electronics",
            ],
            "facilities": [
                "Computer labs with latest systems",
                "Library with digital resources",
                "Sports complex",
                "Hostel facilities",
                "Cafeteria",
                "Wi-Fi campus",
            ],
            "events": [
                "Annual Tech Fest - TechSahyadri",
                "Cultural Fest - Sahyadri Utsav",
                "Workshops and Seminars",
                "Industry visits",
            ],
        }

    def get_response(self, query: str) -> Optional[str]:
        """Try to answer a query based on knowledge base."""
        query_lower = query.lower()

        if "name" in query_lower:
            return f"My name is {self.name}. I'm a student at {self.college['short_name']}."

        if "college" in query_lower or "sahyadri" in query_lower or "engineering" in query_lower:
            return (
                f"I study at {self.college['name']}, located in {self.college['location']}. "
                f"It was established in {self.college['established']} and is affiliated to "
                f"{self.college['affiliated_to']}. The campus is {self.college['campus_size']} "
                f"and it's NAAC accredited with A+ grade."
            )

        if "year" in query_lower or "sem" in query_lower or "semester" in query_lower:
            return (
                f"I'm in my {self.academic['year']}, {self.academic['current_semester']}, "
                f"pursuing {self.academic['program']}. I'm expected to graduate in "
                f"{self.academic['expected_graduation']}."
            )

        if "course" in query_lower or "subject" in query_lower or "study" in query_lower:
            courses = ", ".join(self.courses["current_semester_courses"])
            return (
                f"This semester I'm studying: {courses}. "
                f"Over my degree, I've covered: {', '.join(self.courses['core_cse'][:6])}."
            )

        if "skill" in query_lower or "know" in query_lower or "program" in query_lower:
            langs = ", ".join(self.skills["programming_languages"])
            return (
                f"My programming skills include: {langs}. "
                f"I'm comfortable with {', '.join(self.skills['web_technologies'])} "
                f"for web development, and I use tools like {', '.join(self.skills['tools'])}."
            )

        if "project" in query_lower:
            current = self.projects[0]
            return (
                f"I'm currently working on: {current['name']} using {current['tech']}. "
                f"{current['description']}. {current['status']}."
            )

        if "interest" in query_lower or "hobby" in query_lower or "like" in query_lower:
            return f"My main interests are: {', '.join(self.interests)}."

        if "daily" in query_lower or "routine" in query_lower or "day" in query_lower:
            return (
                f"My typical day: {self.daily_routine['morning']}, "
                f"then {self.daily_routine['afternoon']}, "
                f"followed by {self.daily_routine['evening']}, "
                f"and {self.daily_routine['night']}."
            )

        if "event" in query_lower or "fest" in query_lower:
            return (
                f"Our college hosts {self.college_info['events'][0]} and "
                f"{self.college_info['events'][1]} along with regular workshops."
            )

        if "facility" in query_lower or "lab" in query_lower or "library" in query_lower:
            return f"Our campus has: {', '.join(self.college_info['facilities'][:5])}."

        return None

    def get_intro(self) -> str:
        """Get a personalized introduction."""
        return (
            f"Hello! I'm a {self.academic['year']} {self.academic['program']} student "
            f"at {self.college['name']} in {self.college['location']}. "
            f"I'm passionate about AI, web development, and building cool projects. "
            f"My current project is an AI Digital Twin Assistant using Python and 3D graphics. "
            f"Ask me about my college, courses, projects, or anything else!"
        )

    def get_script(self, language: str = "en") -> str:
        """Generate a 3-minute avatar script in the requested language.

        Args:
            language: Language code ('en', 'kn', 'ta', 'hi')
        """
        base_en = f"""Hello, and welcome to my Digital Twin!

Let me introduce myself. I am a {self.academic['year']} student pursuing {self.academic['program']} at {self.college['name']}. I am currently in my {self.academic['current_semester']} and will be graduating in {self.academic['expected_graduation']}.

My college is located in {self.college['location']}. It is affiliated to {self.college['affiliated_to']} and is NAAC accredited with an A+ grade. The campus spans over 30 acres with excellent facilities including modern computer labs, a well-stocked library, sports complex, and a vibrant campus life.

This semester I am studying Machine Learning, Cloud Computing, Internet of Things, Cyber Security, and working on my final year project. Over the past four years I have learned programming in Python, Java, C, and JavaScript. I have a strong foundation in data structures, algorithms, database management, operating systems, and computer networks.

My current project is an AI Digital Twin Assistant. It is a 3D interactive avatar that can see, speak, and interact with users in real time. I am building it using Python with FastAPI for the backend, Three.js for 3D rendering, and Edge-TTS for realistic voice synthesis. The avatar can detect emotions from text, respond intelligently, and has voice cloning capabilities.

I regularly participate in hackathons and technical events at my college. Our annual tech fest TechSahyadri brings together students from across the region for competitions, workshops, and networking. I enjoy competitive programming and keeping up with the latest developments in AI and web technologies.

My daily routine involves attending lectures and labs in the morning, working on projects in the afternoon, and self-study in the evenings. I believe in continuous learning and try to pick up new skills whenever I can.

Apart from academics, I enjoy exploring new technologies, contributing to open source projects, and building applications that solve real-world problems. I also make time for sports and other extracurricular activities.

Thank you for interacting with my Digital Twin. Feel free to ask me anything about my college experience, my projects, or my interests. I hope this gives you a glimpse into who I am and what I am working on. Let us build something amazing together!"""

        # Language-specific scripts
        language_scripts = {
            "kn": (
                "ನಮಸ್ಕಾರ, ನನ್ನ ಡಿಜಿಟಲ್ ಟ್ವಿನ್‌ಗೆ ಸುಸ್ವಾಗತ!\n\n"
                "ನಾನು ಸಹ್ಯಾದ್ರಿ ಕಾಲೇಜ್ ಆಫ್ ಎಂಜಿನಿಯರಿಂಗ್ ಅಂಡ್ ಮ್ಯಾನೇಜ್‌ಮೆಂಟ್‌ನಲ್ಲಿ "
                "ಕಂಪ್ಯೂಟರ್ ಸೈನ್ಸ್ ಮತ್ತು ಎಂಜಿನಿಯರಿಂಗ್ ವಿಭಾಗದಲ್ಲಿ ನಾಲ್ಕನೇ ವರ್ಷದ ವಿದ್ಯಾರ್ಥಿ. "
                "ನನ್ನ ಕಾಲೇಜು ಮಂಗಳೂರಿನಲ್ಲಿದೆ ಮತ್ತು ವಿಟಿಯು ವಿಶ್ವವಿದ್ಯಾಲಯಕ್ಕೆ ಸಂಯೋಜಿತವಾಗಿದೆ.\n\n"
                "ಈ ಸೆಮಿಸ್ಟರ್‌ನಲ್ಲಿ ನಾನು ಮೆಷಿನ್ ಲರ್ನಿಂಗ್, ಕ್ಲೌಡ್ ಕಂಪ್ಯೂಟಿಂಗ್, ಇಂಟರ್ನೆಟ್ ಆಫ್ ಥಿಂಗ್ಸ್, "
                "ಮತ್ತು ಸೈಬರ್ ಸೆಕ್ಯುರಿಟಿ ವಿಷಯಗಳನ್ನು ಅಧ್ಯಯನ ಮಾಡುತ್ತಿದ್ದೇನೆ. "
                "ನನ್ನ ಪ್ರಸ್ತುತ ಯೋಜನೆ ಎಐ ಡಿಜಿಟಲ್ ಟ್ವಿನ್ ಅಸಿಸ್ಟೆಂಟ್ ಆಗಿದೆ.\n\n"
                "ನಾನು ಪೈಥಾನ್, ಜಾವಾ, ಸಿ ಮತ್ತು ಜಾವಾಸ್ಕ್ರಿಪ್ಟ್ ಭಾಷೆಗಳಲ್ಲಿ ಪ್ರೋಗ್ರಾಮಿಂಗ್ ಮಾಡಬಲ್ಲೆ. "
                "ವೆಬ್ ಅಭಿವೃದ್ಧಿ, ಕೃತಕ ಬುದ್ಧಿಮತ್ತೆ ಮತ್ತು ಕ್ಲೌಡ್ ಕಂಪ್ಯೂಟಿಂಗ್ ನನ್ನ ಆಸಕ್ತಿಯ ಕ್ಷೇತ್ರಗಳು.\n\n"
                "ನನ್ನ ಕಾಲೇಜಿನ ವಾರ್ಷಿಕ ತಂತ್ರಜ್ಞಾನ ಉತ್ಸವ ಟೆಕ್ ಸಹ್ಯಾದ್ರಿಯಲ್ಲಿ ನಾನು ಸಕ್ರಿಯವಾಗಿ ಭಾಗವಹಿಸುತ್ತೇನೆ. "
                "ನನ್ನ ದೈನಂದಿನ ದಿನಚರಿಯಲ್ಲಿ ಬೆಳಿಗ್ಗೆ ತರಗತಿಗಳು, ಮಧ್ಯಾಹ್ನ ಯೋಜನೆಗಳ ಮೇಲೆ ಕೆಲಸ, "
                "ಮತ್ತು ಸಂಜೆ ಸ್ವ-ಅಧ್ಯಯನ ಸೇರಿವೆ.\n\n"
                "ನನ್ನ ಡಿಜಿಟಲ್ ಟ್ವಿನ್‌ನೊಂದಿಗೆ ಸಂವಹನ ನಡೆಸಿದ್ದಕ್ಕಾಗಿ ಧನ್ಯವಾದಗಳು. "
                "ನನ್ನ ಕಾಲೇಜು, ಯೋಜನೆಗಳು ಮತ್ತು ಆಸಕ್ತಿಗಳ ಬಗ್ಗೆ ನಿಮ್ಮ ಪ್ರಶ್ನೆಗಳನ್ನು ಕೇಳಲು ಮರೆಯಬೇಡಿ!"
            ),
            "ta": (
                "வணக்கம், எனது டிஜிட்டல் ட்வின் உங்களை வரவேற்கிறது!\n\n"
                "நான் சஹ்யாத்ரி காலேஜ் ஆஃப் இன்ஜினியரிங் அண்ட் மேனேஜ்மென்டில் "
                "கம்ப்யூட்டர் சயின்ஸ் இன்ஜினியரிங் நான்காம் ஆண்டு மாணவன். "
                "எனது கல்லூரி மங்களூரில் அமைந்துள்ளது மற்றும் விடியூ பல்கலைக்கழகத்துடன் இணைக்கப்பட்டுள்ளது.\n\n"
                "இந்த செமஸ்டரில் மெஷின் லேர்னிங், கிளவுட் கம்ப்யூட்டிங், இன்டர்நெட் ஆஃப் திங்ஸ், "
                "மற்றும் சைபர் செக்யூரிட்டி ஆகிய பாடங்களைப் படிக்கிறேன். "
                "எனது தற்போதைய திட்டம் AI டிஜிட்டல் ட்வின் அசிஸ்டென்ட் ஆகும்.\n\n"
                "நான் பைத்தான், ஜாவா, சி மற்றும் ஜாவாஸ்கிரிப்ட் மொழிகளில் நிரலாக்கம் செய்ய முடியும். "
                "இணைய மேம்பாடு, செயற்கை நுண்ணறிவு மற்றும் கிளவுட் கம்ப்யூட்டிங் எனது ஆர்வமுள்ள துறைகள்.\n\n"
                "எனது கல்லூரியின் வருடாந்திர டெக் ஃபெஸ்ட் டெக் சஹ்யாத்ரியில் நான் தீவிரமாக பங்கேற்கிறேன். "
                "எனது அன்றாட வழக்கத்தில் காலை வகுப்புகள், மதியம் திட்டப் பணிகள், "
                "மற்றும் மாலை சுய கல்வி ஆகியவை அடங்கும்.\n\n"
                "எனது டிஜிட்டல் ட்வினுடன் தொடர்பு கொண்டதற்கு நன்றி. "
                "எனது கல்லூரி, திட்டங்கள் மற்றும் ஆர்வங்கள் பற்றி தயங்காமல் கேளுங்கள்!"
            ),
            "hi": (
                "नमस्ते, मेरे डिजिटल ट्विन में आपका स्वागत है!\n\n"
                "मैं सह्याद्री कॉलेज ऑफ इंजीनियरिंग एंड मैनेजमेंट में "
                "कंप्यूटर साइंस इंजीनियरिंग के चौथे वर्ष का छात्र हूँ। "
                "मेरा कॉलेज मंगलौर में स्थित है और विटीयू विश्वविद्यालय से संबद्ध है।\n\n"
                "इस सेमेस्टर में मैं मशीन लर्निंग, क्लाउड कंप्यूटिंग, इंटरनेट ऑफ थिंग्स, "
                "और साइबर सिक्योरिटी पढ़ रहा हूँ। "
                "मेरी वर्तमान परियोजना AI डिजिटल ट्विन असिस्टेंट है।\n\n"
                "मैं पाइथन, जावा, सी और जावास्क्रिप्ट में प्रोग्रामिंग कर सकता हूँ। "
                "वेब डेवलपमेंट, कृत्रिम बुद्धिमत्ता और क्लाउड कंप्यूटिंग मेरी रुचि के क्षेत्र हैं।\n\n"
                "मैं अपने कॉलेज के वार्षिक टेक फेस्ट टेक सह्याद्री में सक्रिय रूप से भाग लेता हूँ। "
                "मेरी दैनिक दिनचर्या में सुबह कक्षाएं, दोपहर परियोजनाओं पर काम, "
                "और शाम को स्व-अध्ययन शामिल है।\n\n"
                "मेरे डिजिटल ट्विन से बातचीत करने के लिए धन्यवाद। "
                "मेरे कॉलेज, परियोजनाओं और रुचियों के बारे में बेझिझक पूछें!"
            ),
        }

        if language == "en":
            return base_en
        return language_scripts.get(language, base_en)
