"""
BlackDuck MCP Server

Provides Model Context Protocol interface for BlackDuck Hub REST API
"""

import os
import sys
import logging
from typing import List, Dict, Any, Optional
import json

# Configure logging for MCP server
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

try:
    from fastmcp import FastMCP
except ImportError:
    raise ImportError(
        "FastMCP not available. Install with: pip install fastmcp"
    )

from .Client import Client
from .Utils import safe_get


class BlackDuckMCPServer:
    """BlackDuck MCP Server implementation"""
    
    def __init__(self):
        self.mcp = FastMCP("BlackDuck Hub")
        self.client = None
        self._setup_client()
        self._register_tools()
    
    def _setup_client(self):
        """Initialize BlackDuck client from environment variables"""
        base_url = os.environ.get('BLACKDUCK_URL')
        token = os.environ.get('BLACKDUCK_TOKEN')
        
        if not base_url or not token:
            raise ValueError(
                "Missing required environment variables:\n"
                "  BLACKDUCK_URL and BLACKDUCK_TOKEN"
            )
        
        self.client = Client(
            base_url=base_url,
            token=token,
            verify=True,  # Default to secure
            timeout=30.0,
            retries=3
        )
        
        logger.info(f"BlackDuck client initialized for {base_url}")
    
    def _register_tools(self):
        """Register MCP tools"""
        
        @self.mcp.tool
        def list_projects(limit: Optional[int] = 50) -> List[Dict[str, Any]]:
            """List BlackDuck projects
            
            Args:
                limit: Maximum number of projects to return (default: 50)
                
            Returns:
                List of project dictionaries with name, description, and metadata
            """
            try:
                projects = self.client.get_resource('projects')
                result = []
                
                for i, project in enumerate(projects):
                    if limit and i >= limit:
                        break
                        
                    result.append({
                        'name': project.get('name'),
                        'description': project.get('description', ''),
                        'projectOwner': safe_get(project, 'projectOwner'),
                        'createdAt': project.get('createdAt'),
                        'updatedAt': project.get('updatedAt'),
                        '_meta': {
                            'href': project.get('_meta', {}).get('href')
                        }
                    })
                
                return result
                
            except Exception as e:
                logger.error(f"Error listing projects: {e}")
                raise
        
        @self.mcp.tool
        def get_project_details(project_name: str) -> Optional[Dict[str, Any]]:
            """Get detailed information about a specific project
            
            Args:
                project_name: Name of the project to retrieve
                
            Returns:
                Project details dictionary or None if not found
            """
            try:
                params = {'q': [f"name:{project_name}"]}
                projects = list(self.client.get_resource('projects', params=params))
                
                # Find exact match (case-insensitive)
                project = None
                for p in projects:
                    if p['name'].lower() == project_name.lower():
                        project = p
                        break
                
                if not project:
                    return None
                
                return {
                    'name': project.get('name'),
                    'description': project.get('description', ''),
                    'projectOwner': safe_get(project, 'projectOwner'),
                    'createdAt': project.get('createdAt'),
                    'updatedAt': project.get('updatedAt'),
                    'projectLevelAdjustments': project.get('projectLevelAdjustments', False),
                    'cloneCategories': project.get('cloneCategories', []),
                    '_meta': project.get('_meta', {})
                }
                
            except Exception as e:
                logger.error(f"Error getting project details: {e}")
                raise
        
        @self.mcp.tool  
        def list_project_versions(project_name: str, limit: Optional[int] = 20) -> List[Dict[str, Any]]:
            """List versions for a specific project
            
            Args:
                project_name: Name of the project
                limit: Maximum number of versions to return (default: 20)
                
            Returns:
                List of version dictionaries
            """
            try:
                # First find the project
                params = {'q': [f"name:{project_name}"]}
                projects = list(self.client.get_resource('projects', params=params))
                
                project = None
                for p in projects:
                    if p['name'].lower() == project_name.lower():
                        project = p
                        break
                
                if not project:
                    return []
                
                # Get versions for the project
                versions = self.client.get_resource('versions', project)
                result = []
                
                for i, version in enumerate(versions):
                    if limit and i >= limit:
                        break
                        
                    result.append({
                        'versionName': version.get('versionName'),
                        'nickname': version.get('nickname'),
                        'phase': version.get('phase'),
                        'distribution': version.get('distribution'),
                        'createdAt': version.get('createdAt'),
                        'settingUpdatedAt': version.get('settingUpdatedAt'),
                        '_meta': {
                            'href': version.get('_meta', {}).get('href')
                        }
                    })
                
                return result
                
            except Exception as e:
                logger.error(f"Error listing project versions: {e}")
                raise
        
        @self.mcp.tool
        def search_projects(query: str, limit: Optional[int] = 25) -> List[Dict[str, Any]]:
            """Search for projects by name or description
            
            Args:
                query: Search query string
                limit: Maximum number of results to return (default: 25)
                
            Returns:
                List of matching project dictionaries
            """
            try:
                params = {'q': [f"name:{query}"]}
                projects = self.client.get_resource('projects', params=params)
                result = []
                
                for i, project in enumerate(projects):
                    if limit and i >= limit:
                        break
                        
                    # Simple relevance scoring
                    name = project.get('name', '').lower()
                    description = project.get('description', '').lower()
                    query_lower = query.lower()
                    
                    relevance = 0
                    if query_lower in name:
                        relevance += 2
                    if query_lower in description:
                        relevance += 1
                    
                    result.append({
                        'name': project.get('name'),
                        'description': project.get('description', ''),
                        'relevance': relevance,
                        'createdAt': project.get('createdAt'),
                        '_meta': {
                            'href': project.get('_meta', {}).get('href')
                        }
                    })
                
                # Sort by relevance
                result.sort(key=lambda x: x['relevance'], reverse=True)
                return result
                
            except Exception as e:
                logger.error(f"Error searching projects: {e}")
                raise
        
        @self.mcp.tool
        def get_project_vulnerabilities(project_name: str, version_name: Optional[str] = None, limit: Optional[int] = 50) -> List[Dict[str, Any]]:
            """Get vulnerabilities for a project version
            
            Args:
                project_name: Name of the project
                version_name: Name of the version (if None, uses latest)
                limit: Maximum number of vulnerabilities to return (default: 50)
                
            Returns:
                List of vulnerability dictionaries
            """
            try:
                # Find project
                params = {'q': [f"name:{project_name}"]}
                projects = list(self.client.get_resource('projects', params=params))
                
                project = None
                for p in projects:
                    if p['name'].lower() == project_name.lower():
                        project = p
                        break
                
                if not project:
                    return []
                
                # Find version
                versions = list(self.client.get_resource('versions', project))
                if not versions:
                    return []
                
                version = None
                if version_name:
                    for v in versions:
                        if v['versionName'].lower() == version_name.lower():
                            version = v
                            break
                else:
                    # Use first (most recent) version
                    version = versions[0]
                
                if not version:
                    return []
                
                # Get vulnerabilities
                try:
                    vulnerabilities = self.client.get_resource('vulnerable-components', version)
                    result = []
                    
                    for i, vuln in enumerate(vulnerabilities):
                        if limit and i >= limit:
                            break
                            
                        result.append({
                            'componentName': vuln.get('componentName'),
                            'componentVersionName': vuln.get('componentVersionName'),
                            'vulnerabilityName': vuln.get('vulnerabilityName'),
                            'severity': vuln.get('severity'),
                            'baseScore': vuln.get('baseScore'),
                            'overallScore': vuln.get('overallScore'),
                            'remediationStatus': vuln.get('remediationStatus'),
                            'description': vuln.get('description', ''),
                            'publishedDate': vuln.get('publishedDate'),
                            'updatedDate': vuln.get('updatedDate')
                        })
                    
                    return result
                    
                except Exception:
                    # Fallback: try to get components instead
                    components = self.client.get_resource('components', version)
                    return [{'info': 'Use list_project_components for component information'}]
                
            except Exception as e:
                logger.error(f"Error getting vulnerabilities: {e}")
                raise
        
        @self.mcp.tool
        def list_project_components(project_name: str, version_name: Optional[str] = None, limit: Optional[int] = 50) -> List[Dict[str, Any]]:
            """List components in a project version
            
            Args:
                project_name: Name of the project
                version_name: Name of the version (if None, uses latest)  
                limit: Maximum number of components to return (default: 50)
                
            Returns:
                List of component dictionaries
            """
            try:
                # Find project
                params = {'q': [f"name:{project_name}"]}
                projects = list(self.client.get_resource('projects', params=params))
                
                project = None
                for p in projects:
                    if p['name'].lower() == project_name.lower():
                        project = p
                        break
                
                if not project:
                    return []
                
                # Find version
                versions = list(self.client.get_resource('versions', project))
                if not versions:
                    return []
                
                version = None
                if version_name:
                    for v in versions:
                        if v['versionName'].lower() == version_name.lower():
                            version = v
                            break
                else:
                    version = versions[0]
                
                if not version:
                    return []
                
                # Get components
                components = self.client.get_resource('components', version)
                result = []
                
                for i, component in enumerate(components):
                    if limit and i >= limit:
                        break
                        
                    licenses = component.get('licenses', [])
                    license_display = licenses[0].get('licenseDisplay', 'Unknown') if licenses else 'Unknown'
                    
                    result.append({
                        'componentName': component.get('componentName'),
                        'componentVersionName': component.get('componentVersionName'),
                        'matchTypes': component.get('matchTypes', []),
                        'usages': component.get('usages', []),
                        'licenseDisplay': license_display,
                        'policyStatus': component.get('policyStatus'),
                        'securityRiskProfile': component.get('securityRiskProfile'),
                        'activityData': component.get('activityData')
                    })
                
                return result
                
            except Exception as e:
                logger.error(f"Error listing components: {e}")
                raise
    
    def run(self):
        """Run the MCP server"""
        self.mcp.run()


def run_mcp_server():
    """Entry point for running the MCP server"""
    try:
        server = BlackDuckMCPServer()
        server.run()
    except Exception as e:
        logger.error(f"Failed to start MCP server: {e}")
        sys.exit(1)


if __name__ == '__main__':
    run_mcp_server()