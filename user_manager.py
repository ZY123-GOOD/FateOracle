"""用户管理模块 - 处理用户注册、登录和问答次数管理"""

import sqlite3
import hashlib
import uuid
from datetime import datetime
from typing import Optional, Dict, Tuple


class UserManager:
    """用户管理器"""
    
    def __init__(self, db_path: str = "bazi_users.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建用户表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT UNIQUE,
                credits INTEGER DEFAULT 10,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')
        
        # 创建使用记录
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usage_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                action_type TEXT,  -- 'basic_analysis' 或 'qa'
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # 创建排盘历史表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bazi_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                birth_time TEXT NOT NULL,
                gender TEXT,
                city TEXT,
                bazi_result TEXT NOT NULL,  -- JSON格式存储完整排盘结果
                analysis_result TEXT,  -- AI分析结果（可选）
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # 创建问答历史表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS qa_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                bazi_history_id INTEGER,  -- 关联的排盘记录
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (bazi_history_id) REFERENCES bazi_history(id)
            )
        ''')
        
        # 自动创建管理员账号（如果不存在）
        admin_id = "admin_root"
        admin_username = "ROOT"
        admin_password = "123456"
        admin_password_hash = self._hash_password(admin_password)
        admin_email = "admin@bazi.local"
        
        # 检查管理员账号是否存在
        cursor.execute('SELECT id FROM users WHERE username = ?', (admin_username,))
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO users (id, username, password, email, credits)
                VALUES (?, ?, ?, ?, 1000)
            ''', (admin_id, admin_username, admin_password_hash, admin_email))
            print(f"[INFO] 已自动创建管理员账号: {admin_username}")
        
        conn.commit()
        conn.close()
    
    def _hash_password(self, password: str) -> str:
        """密码哈希"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _is_valid_email(self, email: str) -> bool:
        """简单的邮箱格式验证"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def register(self, username: str, password: str, email: str) -> Tuple[bool, str]:
        """
        用户注册（邮箱必填）
        
        Args:
            username: 用户名
            password: 密码
            email: 邮箱（必填）
        
        Returns:
            (成功, 消息)
        """
        if not username or not password:
            return False, "用户名和密码不能为空"
        
        if not email:
            return False, "邮箱地址不能为空"
        
        if not self._is_valid_email(email):
            return False, "请输入有效的邮箱地址"
        
        if len(password) < 6:
            return False, "密码至少需要6位"
        
        user_id = str(uuid.uuid4())
        hashed_pwd = self._hash_password(password)
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO users (id, username, password, email, credits)
                VALUES (?, ?, ?, ?, 10)
            ''', (user_id, username, hashed_pwd, email))
            
            conn.commit()
            conn.close()
            return True, "注册成功，已赠送10次问答机会"
        except sqlite3.IntegrityError as e:
            if "username" in str(e):
                return False, "用户名已存在"
            elif "email" in str(e):
                return False, "邮箱已被注册"
            return False, str(e)
    
    def login(self, username: str, password: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        用户登录
        
        Args:
            username: 用户名
            password: 密码
        
        Returns:
            (成功, 消息, 用户信息)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, username, email, credits, last_login
            FROM users WHERE username = ?
        ''', (username,))
        
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return False, "用户名不存在", None
        
        hashed_pwd = self._hash_password(password)
        cursor.execute('''
            SELECT id, username, email, credits
            FROM users WHERE username = ? AND password = ?
        ''', (username, hashed_pwd))
        
        user = cursor.fetchone()
        
        if user:
            # 更新登录时间
            cursor.execute('''
                UPDATE users SET last_login = ? WHERE id = ?
            ''', (datetime.now(), user[0]))
            conn.commit()
            
            conn.close()
            return True, "登录成功", {
                "id": user[0],
                "username": user[1],
                "email": user[2],
                "credits": user[3]
            }
        
        conn.close()
        return False, "密码错误", None
    
    def check_credits(self, user_id: str) -> int:
        """检查用户剩余次数"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT credits FROM users WHERE id = ?
        ''', (user_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else 0
    
    def consume_credit(self, user_id: str, action_type: str) -> bool:
        """
        消耗一次问答机会
        
        Args:
            user_id: 用户ID
            action_type: 'basic_analysis' 或 'qa'
        
        Returns:
            是否成功
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 检查余额
        cursor.execute('''
            SELECT credits FROM users WHERE id = ?
        ''', (user_id,))
        
        result = cursor.fetchone()
        if not result or result[0] <= 0:
            conn.close()
            return False
        
        # 扣减余额
        cursor.execute('''
            UPDATE users SET credits = credits - 1 WHERE id = ?
        ''', (user_id,))
        
        # 记录日志
        cursor.execute('''
            INSERT INTO usage_logs (user_id, action_type)
            VALUES (?, ?)
        ''', (user_id, action_type))
        
        conn.commit()
        conn.close()
        return True
    
    def get_user_info(self, user_id: str) -> Optional[Dict]:
        """获取用户信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, username, email, credits, created_at, last_login
            FROM users WHERE id = ?
        ''', (user_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                "id": result[0],
                "username": result[1],
                "email": result[2],
                "credits": result[3],
                "created_at": result[4],
                "last_login": result[5]
            }
        return None
    
    def add_credits(self, user_id: str, amount: int) -> bool:
        """增加用户次数"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users SET credits = credits + ? WHERE id = ?
        ''', (amount, user_id))
        
        conn.commit()
        conn.close()
        return cursor.rowcount > 0
    
    def save_bazi_result(self, user_id: str, birth_time: str, gender: str, city: str, bazi_result: str, analysis_result: str = None) -> int:
        """
        保存排盘结果
        
        Args:
            user_id: 用户ID
            birth_time: 出生时间
            gender: 性别
            city: 出生地
            bazi_result: 排盘结果（JSON字符串）
            analysis_result: AI分析结果（可选）
        
        Returns:
            记录ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO bazi_history (user_id, birth_time, gender, city, bazi_result, analysis_result)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, birth_time, gender, city, bazi_result, analysis_result))
        
        record_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return record_id
    
    def get_bazi_history(self, user_id: str, limit: int = 50) -> list:
        """获取用户排盘历史"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, birth_time, gender, city, bazi_result, analysis_result, timestamp
            FROM bazi_history
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (user_id, limit))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row[0],
                'birth_time': row[1],
                'gender': row[2],
                'city': row[3],
                'bazi_result': row[4],
                'analysis_result': row[5],
                'timestamp': row[6]
            })
        
        conn.close()
        return results
    
    def update_bazi_result(self, bazi_history_id: int, analysis_result: str) -> bool:
        """
        更新排盘记录的分析结果
        
        Args:
            bazi_history_id: 排盘记录ID
            analysis_result: AI分析结果
        
        Returns:
            是否成功
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE bazi_history 
            SET analysis_result = ? 
            WHERE id = ?
        ''', (analysis_result, bazi_history_id))
        
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        return affected > 0
    
    def delete_bazi_history(self, user_id: str, history_id: int) -> bool:
        """删除排盘历史记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 先删除关联的问答记录
        cursor.execute('''
            DELETE FROM qa_history WHERE bazi_history_id = ?
        ''', (history_id,))
        
        # 删除排盘记录
        cursor.execute('''
            DELETE FROM bazi_history WHERE id = ? AND user_id = ?
        ''', (history_id, user_id))
        
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        return affected > 0
    
    def get_bazi_history_count(self, user_id: str) -> int:
        """获取用户排盘历史数量"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) FROM bazi_history WHERE user_id = ?
        ''', (user_id,))
        
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 0
    
    def save_qa_history(self, user_id: str, bazi_history_id: int, question: str, answer: str) -> int:
        """
        保存问答记录
        
        Args:
            user_id: 用户ID
            bazi_history_id: 关联的排盘记录ID
            question: 问题
            answer: 回答
        
        Returns:
            记录ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO qa_history (user_id, bazi_history_id, question, answer)
            VALUES (?, ?, ?, ?)
        ''', (user_id, bazi_history_id, question, answer))
        
        record_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return record_id
    
    def get_qa_history_by_bazi(self, user_id: str, bazi_history_id: int) -> list:
        """获取指定排盘的问答历史"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, question, answer, timestamp
            FROM qa_history
            WHERE user_id = ? AND bazi_history_id = ?
            ORDER BY timestamp ASC
        ''', (user_id, bazi_history_id))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row[0],
                'question': row[1],
                'answer': row[2],
                'timestamp': row[3]
            })
        
        conn.close()
        return results


# ========== 测试 ==========
def test_user_manager():
    """测试用户管理功能"""
    um = UserManager(":memory:")  # 内存数据库测试
    
    # 测试注册
    success, msg = um.register("testuser", "password123")
    print(f"注册: {success} - {msg}")
    
    # 测试重复注册
    success, msg = um.register("testuser", "password123")
    print(f"重复注册: {success} - {msg}")
    
    # 测试登录
    success, msg, user = um.login("testuser", "password123")
    print(f"登录: {success} - {msg}")
    print(f"用户信息: {user}")
    
    # 测试检查余额
    credits = um.check_credits(user["id"])
    print(f"初始余额: {credits}")
    
    # 测试消耗
    success = um.consume_credit(user["id"], "qa")
    print(f"消耗: {success}")
    
    credits = um.check_credits(user["id"])
    print(f"消耗后余额: {credits}")
    
    # 测试耗尽
    for _ in range(9):
        um.consume_credit(user["id"], "qa")
    
    credits = um.check_credits(user["id"])
    print(f"耗尽后余额: {credits}")
    
    success = um.consume_credit(user["id"], "qa")
    print(f"耗尽后尝试消耗: {success}")


if __name__ == "__main__":
    test_user_manager()