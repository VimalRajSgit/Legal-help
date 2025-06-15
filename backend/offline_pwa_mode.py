import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import sqlite3
import hashlib

class OfflinePWAMode:
    def __init__(self):
        self.cache_dir = "cache"
        self.db_path = os.path.join(self.cache_dir, "offline_data.db")
        self.max_cache_size = 50 * 1024 * 1024  # 50MB
        self.cache_duration = timedelta(days=7)  # Cache for 7 days
        
        # Create cache directory
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Initialize database
        self.init_database()
        
        # Offline legal knowledge base
        self.offline_knowledge_base = {
            "common_legal_terms": {
                "ವಿವಾಹ ವಿಚ್ಛೇದನ": {
                    "definition": "ವಿವಾಹ ಬಂಧನವನ್ನು ಕಾನೂನುಬದ್ಧವಾಗಿ ಕೊನೆಗೊಳಿಸುವ ಪ್ರಕ್ರಿಯೆ",
                    "process": ["ಅರ್ಜಿ ಸಲ್ಲಿಸುವುದು", "ನ್ಯಾಯಾಲಯದ ವಿಚಾರಣೆ", "ತೀರ್ಪು"],
                    "documents_needed": ["ವಿವಾಹ ಪ್ರಮಾಣಪತ್ರ", "ಗುರುತಿನ ಪುರಾವೆ", "ವಿಳಾಸದ ಪುರಾವೆ"]
                },
                "ಆಸ್ತಿ ವಿವಾದ": {
                    "definition": "ಆಸ್ತಿ ಹಕ್ಕುಗಳ ಬಗ್ಗೆ ಭಿನ್ನಾಭಿಪ್ರಾಯ",
                    "process": ["ದಾಖಲೆಗಳ ಪರಿಶೀಲನೆ", "ಮಧ್ಯಸ್ಥಿಕೆ", "ನ್ಯಾಯಾಲಯದ ಮೊರೆ"],
                    "documents_needed": ["ಆಸ್ತಿ ದಾಖಲೆಗಳು", "ಖರೀದಿ ಒಪ್ಪಂದ", "ತೆರಿಗೆ ರಸೀದಿಗಳು"]
                },
                "ಕಾರ್ಮಿಕ ಹಕ್ಕುಗಳು": {
                    "definition": "ಕೆಲಸಗಾರರ ಕಾನೂನುಬದ್ಧ ಹಕ್ಕುಗಳು",
                    "process": ["ದೂರು ದಾಖಲಿಸುವುದು", "ಕಾರ್ಮಿಕ ಇಲಾಖೆಗೆ ಮನವಿ", "ನ್ಯಾಯಾಲಯದ ಮೊರೆ"],
                    "documents_needed": ["ಉದ್ಯೋಗ ಒಪ್ಪಂದ", "ಸಂಬಳ ಪರ್ಚಿಗಳು", "ಗುರುತಿನ ಪುರಾವೆ"]
                },
                "ಗ್ರಾಹಕ ಹಕ್ಕುಗಳು": {
                    "definition": "ಗ್ರಾಹಕರ ಕಾನೂನುಬದ್ಧ ಹಕ್ಕುಗಳು ಮತ್ತು ರಕ್ಷಣೆ",
                    "process": ["ದೂರು ದಾಖಲಿಸುವುದು", "ಗ್ರಾಹಕ ನ್ಯಾಯಾಲಯಕ್ಕೆ ಮನವಿ", "ಪರಿಹಾರ ಪಡೆಯುವುದು"],
                    "documents_needed": ["ಖರೀದಿ ರಸೀದಿ", "ಉತ್ಪಾದನೆಯ ವಾರಂಟಿ", "ದೂರಿನ ಪುರಾವೆ"]
                }
            },
            "legal_procedures": {
                "ಎಫ್‌ಐಆರ್ ದಾಖಲಿಸುವುದು": {
                    "steps": [
                        "ಹತ್ತಿರದ ಪೊಲೀಸ್ ಠಾಣೆಗೆ ಹೋಗಿ",
                        "ಘಟನೆಯ ವಿವರಗಳನ್ನು ನೀಡಿ",
                        "ಲಿಖಿತ ದೂರು ಸಲ್ಲಿಸಿ",
                        "ಎಫ್‌ಐಆರ್ ಸಂಖ್ಯೆ ಪಡೆಯಿರಿ"
                    ],
                    "documents": ["ಗುರುತಿನ ಪುರಾವೆ", "ವಿಳಾಸದ ಪುರಾವೆ", "ಘಟನೆಯ ಪುರಾವೆಗಳು"],
                    "time_limit": "ಘಟನೆಯ ನಂತರ ಆದಷ್ಟು ಬೇಗ"
                },
                "ಜಾಮೀನು ಅರ್ಜಿ": {
                    "steps": [
                        "ವಕೀಲರನ್ನು ಸಂಪರ್ಕಿಸಿ",
                        "ಜಾಮೀನು ಅರ್ಜಿ ತಯಾರಿಸಿ",
                        "ನ್ಯಾಯಾಲಯದಲ್ಲಿ ಸಲ್ಲಿಸಿ",
                        "ವಿಚಾರಣೆಗೆ ಹಾಜರಾಗಿ"
                    ],
                    "documents": ["ಗುರುತಿನ ಪುರಾವೆ", "ವಿಳಾಸದ ಪುರಾವೆ", "ಜಾಮೀನುದಾರರ ವಿವರಗಳು"],
                    "time_limit": "ಬಂಧನದ ನಂತರ 24 ಗಂಟೆಗಳೊಳಗೆ"
                }
            },
            "emergency_contacts": [
                {"name": "ಪೊಲೀಸ್", "number": "100"},
                {"name": "ಮಹಿಳಾ ಸಹಾಯವಾಣಿ", "number": "1091"},
                {"name": "ಮಕ್ಕಳ ಸಹಾಯವಾಣಿ", "number": "1098"},
                {"name": "ಕಾನೂನು ಸಹಾಯ", "number": "15100"}
            ]
        }

    def init_database(self):
        """Initialize SQLite database for offline storage"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create tables
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT NOT NULL,
                    response TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    user_type TEXT DEFAULT 'user',
                    is_synced BOOLEAN DEFAULT FALSE
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cached_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    value TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    expires_at DATETIME
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    preference_key TEXT UNIQUE NOT NULL,
                    preference_value TEXT NOT NULL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Error initializing database: {e}")

    def cache_conversation_data(self, conversation_data: List[Dict], user_preferences: Dict = None) -> Dict:
        """Cache conversation data for offline access"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cached_count = 0
            
            # Cache conversations
            for conversation in conversation_data:
                cursor.execute('''
                    INSERT OR REPLACE INTO conversations (query, response, user_type, timestamp)
                    VALUES (?, ?, ?, ?)
                ''', (
                    conversation.get('query', ''),
                    conversation.get('response', ''),
                    conversation.get('user_type', 'user'),
                    conversation.get('timestamp', datetime.now().isoformat())
                ))
                cached_count += 1
            
            # Cache user preferences
            if user_preferences:
                for key, value in user_preferences.items():
                    cursor.execute('''
                        INSERT OR REPLACE INTO user_preferences (preference_key, preference_value)
                        VALUES (?, ?)
                    ''', (key, json.dumps(value)))
            
            conn.commit()
            conn.close()
            
            # Clean old cache data
            self.cleanup_old_cache()
            
            return {
                'cached_count': cached_count,
                'cache_size': self.get_cache_size()
            }
            
        except Exception as e:
            print(f"Error caching conversation data: {e}")
            return {'cached_count': 0, 'cache_size': 0}

    def get_cached_data(self) -> Dict:
        """Retrieve cached data for offline use"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get recent conversations
            cursor.execute('''
                SELECT query, response, user_type, timestamp
                FROM conversations
                ORDER BY timestamp DESC
                LIMIT 50
            ''')
            conversations = [
                {
                    'query': row[0],
                    'response': row[1],
                    'user_type': row[2],
                    'timestamp': row[3]
                }
                for row in cursor.fetchall()
            ]
            
            # Get user preferences
            cursor.execute('SELECT preference_key, preference_value FROM user_preferences')
            preferences = {row[0]: json.loads(row[1]) for row in cursor.fetchall()}
            
            conn.close()
            
            return {
                'conversations': conversations,
                'preferences': preferences,
                'knowledge_base': self.offline_knowledge_base,
                'cache_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error getting cached data: {e}")
            return {
                'conversations': [],
                'preferences': {},
                'knowledge_base': self.offline_knowledge_base,
                'cache_timestamp': datetime.now().isoformat()
            }

    def process_offline_query(self, query: str) -> Dict:
        """Process query using offline knowledge base"""
        try:
            query_lower = query.lower().strip()
            
            # Search in knowledge base
            response = self.search_offline_knowledge(query_lower)
            
            if response:
                # Save offline query for later sync
                self.save_offline_query(query, response)
                
                return {
                    'response': response,
                    'source': 'offline_knowledge_base',
                    'confidence': 0.8
                }
            else:
                # Provide generic offline response
                generic_response = self.get_generic_offline_response()
                self.save_offline_query(query, generic_response)
                
                return {
                    'response': generic_response,
                    'source': 'generic_offline',
                    'confidence': 0.3
                }
                
        except Exception as e:
            print(f"Error processing offline query: {e}")
            return {
                'response': "ಕ್ಷಮಿಸಿ, ಆಫ್‌ಲೈನ್ ಮೋಡ್‌ನಲ್ಲಿ ಈ ಪ್ರಶ್ನೆಗೆ ಉತ್ತರಿಸಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ। ದಯವಿಟ್ಟು ಇಂಟರ್ನೆಟ್ ಸಂಪರ್ಕ ಪುನಃಸ್ಥಾಪಿಸಿ.",
                'source': 'error',
                'confidence': 0.0
            }

    def search_offline_knowledge(self, query: str) -> Optional[str]:
        """Search for relevant information in offline knowledge base"""
        try:
            # Search in common legal terms
            for term, info in self.offline_knowledge_base['common_legal_terms'].items():
                if term.lower() in query or any(keyword in query for keyword in term.lower().split()):
                    response = f"**{term}**\n\n"
                    response += f"ವ್ಯಾಖ್ಯೆ: {info['definition']}\n\n"
                    
                    if 'process' in info:
                        response += "ಪ್ರಕ್ರಿಯೆ:\n"
                        for i, step in enumerate(info['process'], 1):
                            response += f"{i}. {step}\n"
                        response += "\n"
                    
                    if 'documents_needed' in info:
                        response += "ಅಗತ್ಯ ದಾಖಲೆಗಳು:\n"
                        for doc in info['documents_needed']:
                            response += f"• {doc}\n"
                    
                    return response
            
            # Search in legal procedures
            for procedure, info in self.offline_knowledge_base['legal_procedures'].items():
                if procedure.lower() in query or any(keyword in query for keyword in procedure.lower().split()):
                    response = f"**{procedure}**\n\n"
                    
                    if 'steps' in info:
                        response += "ಹಂತಗಳು:\n"
                        for i, step in enumerate(info['steps'], 1):
                            response += f"{i}. {step}\n"
                        response += "\n"
                    
                    if 'documents' in info:
                        response += "ಅಗತ್ಯ ದಾಖಲೆಗಳು:\n"
                        for doc in info['documents']:
                            response += f"• {doc}\n"
                        response += "\n"
                    
                    if 'time_limit' in info:
                        response += f"ಸಮಯ ಮಿತಿ: {info['time_limit']}\n"
                    
                    return response
            
            # Check for emergency contact requests
            if any(word in query for word in ['ತುರ್ತು', 'ಸಹಾಯ', 'ಸಂಪರ್ಕ', 'ಸಂಖ್ಯೆ']):
                response = "**ತುರ್ತು ಸಂಪರ್ಕ ಸಂಖ್ಯೆಗಳು:**\n\n"
                for contact in self.offline_knowledge_base['emergency_contacts']:
                    response += f"• {contact['name']}: {contact['number']}\n"
                return response
            
            return None
            
        except Exception as e:
            print(f"Error searching offline knowledge: {e}")
            return None

    def get_generic_offline_response(self) -> str:
        """Get generic response for offline mode"""
        return """ಕ್ಷಮಿಸಿ, ನಾನು ಪ್ರಸ್ತುತ ಆಫ್‌ಲೈನ್ ಮೋಡ್‌ನಲ್ಲಿದ್ದೇನೆ ಮತ್ತು ಸೀಮಿತ ಮಾಹಿತಿ ಮಾತ್ರ ಲಭ್ಯವಿದೆ.

**ಸಾಮಾನ್ಯ ಸಲಹೆ:**
• ಯಾವುದೇ ಕಾನೂನು ಸಮಸ್ಯೆಗಾಗಿ ವಕೀಲರನ್ನು ಸಂಪರ್ಕಿಸಿ
• ಅಗತ್ಯ ದಾಖಲೆಗಳನ್ನು ಸಂಗ್ರಹಿಸಿ
• ಸ್ಥಳೀಯ ಕಾನೂನು ಸಹಾಯ ಕೇಂದ್ರಗಳನ್ನು ಭೇಟಿ ಮಾಡಿ

**ತುರ್ತು ಸಂಪರ್ಕ:**
• ಪೊಲೀಸ್: 100
• ಕಾನೂನು ಸಹಾಯ: 15100

ಇಂಟರ್ನೆಟ್ ಸಂಪರ್ಕ ಪುನಃಸ್ಥಾಪಿಸಿದ ನಂತರ ಹೆಚ್ಚು ವಿವರವಾದ ಸಹಾಯಕ್ಕಾಗಿ ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ."""

    def save_offline_query(self, query: str, response: str):
        """Save offline query for later synchronization"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO conversations (query, response, user_type, is_synced)
                VALUES (?, ?, ?, ?)
            ''', (query, response, 'offline', False))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Error saving offline query: {e}")

    def sync_offline_data(self, offline_conversations: List[Dict]) -> Dict:
        """Synchronize offline data when connection is restored"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            synced_count = 0
            
            # Mark offline conversations as synced
            cursor.execute('UPDATE conversations SET is_synced = TRUE WHERE is_synced = FALSE')
            synced_count = cursor.rowcount
            
            # Add any new offline conversations
            for conversation in offline_conversations:
                cursor.execute('''
                    INSERT INTO conversations (query, response, user_type, is_synced)
                    VALUES (?, ?, ?, ?)
                ''', (
                    conversation.get('query', ''),
                    conversation.get('response', ''),
                    conversation.get('user_type', 'offline'),
                    True
                ))
                synced_count += 1
            
            conn.commit()
            conn.close()
            
            return {
                'synced_count': synced_count,
                'sync_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error syncing offline data: {e}")
            return {'synced_count': 0, 'sync_timestamp': datetime.now().isoformat()}

    def get_cache_size(self) -> int:
        """Get current cache size in bytes"""
        try:
            total_size = 0
            
            # Database size
            if os.path.exists(self.db_path):
                total_size += os.path.getsize(self.db_path)
            
            # Other cache files
            for root, dirs, files in os.walk(self.cache_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    if os.path.exists(file_path):
                        total_size += os.path.getsize(file_path)
            
            return total_size
            
        except Exception as e:
            print(f"Error calculating cache size: {e}")
            return 0

    def cleanup_old_cache(self):
        """Clean up old cache data to maintain size limits"""
        try:
            # Check if cache size exceeds limit
            if self.get_cache_size() > self.max_cache_size:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Delete old conversations (keep only last 100)
                cursor.execute('''
                    DELETE FROM conversations 
                    WHERE id NOT IN (
                        SELECT id FROM conversations 
                        ORDER BY timestamp DESC 
                        LIMIT 100
                    )
                ''')
                
                # Delete expired cached data
                cursor.execute('''
                    DELETE FROM cached_data 
                    WHERE expires_at < datetime('now')
                ''')
                
                conn.commit()
                conn.close()
                
        except Exception as e:
            print(f"Error cleaning up cache: {e}")

    def export_offline_data(self) -> str:
        """Export offline data for backup"""
        try:
            cached_data = self.get_cached_data()
            
            export_file = os.path.join(self.cache_dir, f"offline_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(cached_data, f, ensure_ascii=False, indent=2)
            
            return export_file
            
        except Exception as e:
            print(f"Error exporting offline data: {e}")
            return ""

    def import_offline_data(self, import_file: str) -> bool:
        """Import offline data from backup"""
        try:
            if not os.path.exists(import_file):
                return False
            
            with open(import_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Import conversations
            if 'conversations' in data:
                self.cache_conversation_data(data['conversations'], data.get('preferences', {}))
            
            return True
            
        except Exception as e:
            print(f"Error importing offline data: {e}")
            return False

    def get_offline_statistics(self) -> Dict:
        """Get statistics about offline usage"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Total conversations
            cursor.execute('SELECT COUNT(*) FROM conversations')
            total_conversations = cursor.fetchone()[0]
            
            # Offline conversations
            cursor.execute('SELECT COUNT(*) FROM conversations WHERE user_type = "offline"')
            offline_conversations = cursor.fetchone()[0]
            
            # Unsynced conversations
            cursor.execute('SELECT COUNT(*) FROM conversations WHERE is_synced = FALSE')
            unsynced_conversations = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total_conversations': total_conversations,
                'offline_conversations': offline_conversations,
                'unsynced_conversations': unsynced_conversations,
                'cache_size_mb': round(self.get_cache_size() / (1024 * 1024), 2),
                'knowledge_base_terms': len(self.offline_knowledge_base['common_legal_terms']),
                'emergency_contacts': len(self.offline_knowledge_base['emergency_contacts'])
            }
            
        except Exception as e:
            print(f"Error getting offline statistics: {e}")
            return {}
