# module.py

from abc import ABC, abstractmethod

from jinja2 import Environment, Template


class BaseModule(ABC):
    """Abstract base class for modules.

    All modules should inherit from this class and implement the required methods.
    """

    @property
    @abstractmethod
    def name(self):
        """Get the unique name of the module.

        Returns:
            str: Unique identifier for the module (e.g., 'clock', 'weather').
        """
        pass

    @abstractmethod
    def render(self):
        """Render the module's UI as an HTML string.

        This method must be implemented by each module to provide its specific HTML output.

        Returns:
            str: HTML content representing the module's UI.
        """
        pass

    def update(self):
        """Update the module's state.

        This method can be overridden by subclasses if dynamic updates are required.
        By default, it performs no action.
        """
        pass

    def render_template(self, template_path: str, **context) -> str:
        """
        Renders an HTML template file with the provided context and returns the result as a string.

        Args:
            template_path (str): The full file path to the HTML template
                (e.g., `'templates/index.html'`).
            context (dict): A dictionary containing the variables to be rendered in the template
                (e.g., `title='Hello', message='Welcome!'`).

        Returns:
            str: The rendered HTML content as a string.

        Raises:
            FileNotFoundError: If the specified template file does not exist.
            IOError: If there is an issue reading the file.
        """
        with open(template_path, 'r', encoding='utf-8') as file:
            template_content = file.read()
        template = Template(template_content)
        rendered_html = template.render(context)
        return rendered_html


class APIModule(BaseModule):
    """Abstract base class for modules that expose backend API endpoints.

    Inherits from BaseModule and requires the implementation of the api method.
    """

    @abstractmethod
    def api(self):
        """Return API data for the module.

        Modules that expose backend API endpoints must implement this method
        to return a dictionary containing the API data.

        Returns:
            dict: API data for the module.
        """
        pass
