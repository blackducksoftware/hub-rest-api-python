import logging
from .Client import Client
from .Exceptions import ProjectNotFound

logger = logging.getLogger(__name__)

class Client(Client):
    def get_project_by_name(self, project_name):
        """GET a project object by its name.

        Args:
            project_name (str): of project

        Returns:
            json/dict: requested object or None

        Raises:
            requests.exceptions.HTTPError: from response.raise_for_status()
            json.JSONDecodeError: if response.text is not json
        """
        params = {
            'q': [f"name:{project_name}"]
        }
        filtered_projects = [p for p in self.get_items("/api/projects", params=params) if p.get('name') == project_name]
        assert len(filtered_projects) in [0,1], f"We either found the project or we didn't, but we should never find this many ({len(filtered_projects)})"

        project_obj = filtered_projects[0] if filtered_projects else None
        return project_obj

    def get_project_version_by_name(self, project_name, version_name):
        """GET a project-version object by its name.

        Args:
            project_name (str): of project
            version_name (str): of version

        Returns:
            json/dict tuple: requested project and version objects or None, None

        Raises:
            requests.exceptions.HTTPError: from response.raise_for_status()
            json.JSONDecodeError: if response.text is not json
        """
        project_obj = self.get_project_by_name(project_name)

        if not project_obj:
            logger.warning(f"Did not find project {project_name} on server at {self.base_url}")
            return None, None

        params = {
            'q': [f"name:{version_name}"]
        }

        filtered_versions = [v for v in self.get_resource("versions", project_obj, params=params) if v.get('versionName') == version_name]
        assert len(filtered_versions) in [0,1], f"We either found the version or we didn't, but we should never find this many ({len(filtered_versions)})"

        version_obj = filtered_versions[0] if filtered_versions else None
        return project_obj, version_obj
