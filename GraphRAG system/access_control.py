
from typing import List, Dict, Any, Optional, Set
from enum import Enum
import jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
import logging
from dataclasses import dataclass

from ..config import config
from ..models.graph_entities import GraphNode, NodeType

logger = logging.getLogger(__name__)

class Permission(Enum):
    """Access permissions for graph operations"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"

@dataclass
class AccessPolicy:
    """Access policy definition"""
    node_types: Set[NodeType]
    access_levels: Set[int]
    permissions: Set[Permission]
    conditions: Dict[str, Any]

class AccessController:
    """Mandatory Access Control (MAC) system for GraphRAG"""
    
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.secret_key = config.secret_key
        self.algorithm = config.algorithm
        self.access_token_expire_minutes = config.access_token_expire_minutes
        
        # Access control matrix
        self.access_matrix = self._initialize_access_matrix()
        
        # Role-based access control
        self.role_permissions = self._initialize_role_permissions()
        
        # Dynamic access policies
        self.policies: List[AccessPolicy] = []
        
    def _initialize_access_matrix(self) -> Dict[int, Dict[str, Set[Permission]]]:
        """Initialize the access level matrix (0-5)"""
        return {
            0: {  # Public
                "PERSON": {Permission.READ},
                "CONCEPT": {Permission.READ},
                "DOCUMENT": {Permission.READ},
                "CHUNK": {Permission.READ},
                "TASK": {Permission.READ},
                "GOAL": set(),
                "TOOL": set(),
                "CODE_FILE": set(),
                "MEMORY_EPISODE": set(),
                "OBSERVATION": set(),
                "INSIGHT": set(),
                "PLAN": set(),
                "COMMAND": set(),
                "SYSTEM_STATE": set()
            },
            1: {  # Basic User
                "PERSON": {Permission.READ, Permission.WRITE},
                "CONCEPT": {Permission.READ, Permission.WRITE},
                "DOCUMENT": {Permission.READ, Permission.WRITE},
                "CHUNK": {Permission.READ, Permission.WRITE},
                "TASK": {Permission.READ, Permission.WRITE},
                "GOAL": {Permission.READ},
                "TOOL": {Permission.READ},
                "CODE_FILE": set(),
                "MEMORY_EPISODE": set(),
                "OBSERVATION": set(),
                "INSIGHT": {Permission.READ},
                "PLAN": set(),
                "COMMAND": set(),
                "SYSTEM_STATE": set()
            },
            2: {  # Advanced User
                "PERSON": {Permission.READ, Permission.WRITE},
                "CONCEPT": {Permission.READ, Permission.WRITE},
                "DOCUMENT": {Permission.READ, Permission.WRITE},
                "CHUNK": {Permission.READ, Permission.WRITE},
                "TASK": {Permission.READ, Permission.WRITE},
                "GOAL": {Permission.READ, Permission.WRITE},
                "TOOL": {Permission.READ, Permission.WRITE},
                "CODE_FILE": {Permission.READ},
                "MEMORY_EPISODE": {Permission.READ},
                "OBSERVATION": {Permission.READ},
                "INSIGHT": {Permission.READ, Permission.WRITE},
                "PLAN": {Permission.READ},
                "COMMAND": set(),
                "SYSTEM_STATE": {Permission.READ}
            },
            3: {  # Developer
                "PERSON": {Permission.READ, Permission.WRITE},
                "CONCEPT": {Permission.READ, Permission.WRITE},
                "DOCUMENT": {Permission.READ, Permission.WRITE},
                "CHUNK": {Permission.READ, Permission.WRITE},
                "TASK": {Permission.READ, Permission.WRITE},
                "GOAL": {Permission.READ, Permission.WRITE},
                "TOOL": {Permission.READ, Permission.WRITE},
                "CODE_FILE": {Permission.READ, Permission.WRITE},
                "MEMORY_EPISODE": {Permission.READ, Permission.WRITE},
                "OBSERVATION": {Permission.READ, Permission.WRITE},
                "INSIGHT": {Permission.READ, Permission.WRITE},
                "PLAN": {Permission.READ, Permission.WRITE},
                "COMMAND": {Permission.READ},
                "SYSTEM_STATE": {Permission.READ, Permission.WRITE}
            },
            4: {  # System Admin
                "PERSON": {Permission.READ, Permission.WRITE, Permission.DELETE},
                "CONCEPT": {Permission.READ, Permission.WRITE, Permission.DELETE},
                "DOCUMENT": {Permission.READ, Permission.WRITE, Permission.DELETE},
                "CHUNK": {Permission.READ, Permission.WRITE, Permission.DELETE},
                "TASK": {Permission.READ, Permission.WRITE, Permission.DELETE},
                "GOAL": {Permission.READ, Permission.WRITE, Permission.DELETE},
                "TOOL": {Permission.READ, Permission.WRITE, Permission.DELETE},
                "CODE_FILE": {Permission.READ, Permission.WRITE, Permission.DELETE},
                "MEMORY_EPISODE": {Permission.READ, Permission.WRITE, Permission.DELETE},
                "OBSERVATION": {Permission.READ, Permission.WRITE, Permission.DELETE},
                "INSIGHT": {Permission.READ, Permission.WRITE, Permission.DELETE},
                "PLAN": {Permission.READ, Permission.WRITE, Permission.DELETE},
                "COMMAND": {Permission.READ, Permission.WRITE},
                "SYSTEM_STATE": {Permission.READ, Permission.WRITE, Permission.DELETE}
            },
            5: {  # Super User (AI Agents)
                "PERSON": {Permission.READ, Permission.WRITE},
                "CONCEPT": {Permission.READ, Permission.WRITE},
                "DOCUMENT": {Permission.READ, Permission.WRITE},
                "CHUNK": {Permission.READ, Permission.WRITE},
                "TASK": {Permission.READ, Permission.WRITE},
                "GOAL": {Permission.READ, Permission.WRITE},
                "TOOL": {Permission.READ, Permission.WRITE},
                "CODE_FILE": {Permission.READ, Permission.WRITE},
                "MEMORY_EPISODE": {Permission.READ, Permission.WRITE},
                "OBSERVATION": {Permission.READ, Permission.WRITE},
                "INSIGHT": {Permission.READ, Permission.WRITE},
                "PLAN": {Permission.READ, Permission.WRITE},
                "COMMAND": {Permission.READ, Permission.WRITE},
                "SYSTEM_STATE": {Permission.READ, Permission.WRITE}
            }
        }
    
    def _initialize_role_permissions(self) -> Dict[str, int]:
        """Initialize role-based access levels"""
        return {
            "public": 0,
            "user": 1,
            "advanced_user": 2,
            "developer": 3,
            "admin": 4,
            "ai_agent": 5
        }
    
    def hash_password(self, password: str) -> str:
        """Hash password for storage"""
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.PyJWTError:
            return None
    
    def can_access_node(self, 
                       user_access_level: int, 
                       node: GraphNode, 
                       permission: Permission) -> bool:
        """Check if user can access node with specific permission"""
        
        # Check basic access level
        if user_access_level < node.access_level:
            return False
        
        # Check permission in access matrix
        if user_access_level in self.access_matrix:
            node_permissions = self.access_matrix[user_access_level].get(node.type.value, set())
            if permission not in node_permissions:
                return False
        
        # Check dynamic policies
        for policy in self.policies:
            if self._policy_applies(policy, node, user_access_level):
                if permission not in policy.permissions:
                    return False
        
        return True
    
    def _policy_applies(self, policy: AccessPolicy, node: GraphNode, user_access_level: int) -> bool:
        """Check if access policy applies to node"""
        # Check node type
        if node.type not in policy.node_types:
            return False
        
        # Check access level
        if user_access_level not in policy.access_levels:
            return False
        
        # Check additional conditions
        for condition_key, condition_value in policy.conditions.items():
            node_value = node.metadata.get(condition_key)
            if node_value != condition_value:
                return False
        
        return True
    
    def filter_nodes_by_access(self, 
                              nodes: List[GraphNode], 
                              user_access_level: int, 
                              permission: Permission = Permission.READ) -> List[GraphNode]:
        """Filter nodes based on user access level and permission"""
        return [
            node for node in nodes 
            if self.can_access_node(user_access_level, node, permission)
        ]
    
    def create_policy(self, 
                     name: str,
                     node_types: List[NodeType], 
                     access_levels: List[int], 
                     permissions: List[Permission],
                     conditions: Dict[str, Any] = None) -> AccessPolicy:
        """Create a new access policy"""
        policy = AccessPolicy(
            node_types=set(node_types),
            access_levels=set(access_levels),
            permissions=set(permissions),
            conditions=conditions or {}
        )
        self.policies.append(policy)
        logger.info(f"Created access policy: {name}")
        return policy
    
    def get_effective_permissions(self, 
                                 user_access_level: int, 
                                 node_type: NodeType) -> Set[Permission]:
        """Get effective permissions for user on node type"""
        effective_permissions = set()
        
        # Base permissions from access matrix
        if user_access_level in self.access_matrix:
            effective_permissions.update(
                self.access_matrix[user_access_level].get(node_type.value, set())
            )
        
        # Apply policy modifications
        for policy in self.policies:
            if (node_type in policy.node_types and 
                user_access_level in policy.access_levels):
                effective_permissions.update(policy.permissions)
        
        return effective_permissions
    
    def audit_access(self, 
                    user_id: str, 
                    action: str, 
                    node_id: str, 
                    granted: bool, 
                    reason: str = "") -> Dict[str, Any]:
        """Create access audit entry"""
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "action": action,
            "node_id": node_id,
            "granted": granted,
            "reason": reason
        }
        
        logger.info(f"Access audit: {audit_entry}")
        return audit_entry
    
    def encrypt_sensitive_data(self, data: str, access_level: int = 3) -> str:
        """Encrypt sensitive data based on access level"""
        if access_level < 3:
            return data  # No encryption for low sensitivity
        
        # In practice, use proper encryption
        # This is a placeholder implementation
        from cryptography.fernet import Fernet
        import base64
        
        # Generate or retrieve encryption key based on access level
        key = base64.urlsafe_b64encode(f"encryption_key_{access_level}".encode()[:32].ljust(32, b'0'))
        f = Fernet(key)
        
        encrypted_data = f.encrypt(data.encode())
        return encrypted_data.decode()
    
    def decrypt_sensitive_data(self, encrypted_data: str, access_level: int = 3) -> str:
        """Decrypt sensitive data if user has sufficient access level"""
        if access_level < 3:
            return encrypted_data  # No decryption needed
        
        from cryptography.fernet import Fernet
        import base64
        
        key = base64.urlsafe_b64encode(f"encryption_key_{access_level}".encode()[:32].ljust(32, b'0'))
        f = Fernet(key)
        
        try:
            decrypted_data = f.decrypt(encrypted_data.encode())
            return decrypted_data.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return "[ENCRYPTED DATA]"
