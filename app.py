# app.py
"""
Main Flask application for the Smart Mirror project.

This application dynamically loads modules based on the configuration in config.py
and renders them into the appropriate positions in the HTML template.
"""

import importlib
from flask import Flask, render_template, jsonify
from config import MODULE_LAYOUT


app = Flask(__name__)
loaded_modules = {}


@app.route('/')
def index():
    """Render the main page with modules loaded as per configuration.

    Returns:
        str: Rendered HTML page.
    """
    modules_by_position = {}

    # Iterate through each module specified in the configuration.
    for mod_name, mod_config in MODULE_LAYOUT.items():
        try:
            # Dynamically import the module from the modules directory.
            mod_module = importlib.import_module(f"modules.{mod_name}")
            mod_instance = mod_module.get_module()
            loaded_modules[mod_name] = mod_instance
            position = mod_config.get("position", "default")
            # Get the module's HTML content.
            rendered_html = mod_instance.render()
            # Group module output by its configured position.
            modules_by_position.setdefault(position, []).append(rendered_html)
        except Exception as e:
            print(f"Failed to load module '{mod_name}': {e}")
            continue

    return render_template("index.html", modules=modules_by_position)


def register_api_endpoints():
    """Automatically register API endpoints for modules with an 'api_endpoint' defined."""
    for mod_name, mod_config in MODULE_LAYOUT.items():
        if 'api_endpoint' in mod_config:
            try:
                # Ensure the module instance is loaded.
                mod_instance = loaded_modules.get(mod_name)
                if mod_instance is None:
                    mod_module = importlib.import_module(f"modules.{mod_name}")
                    mod_instance = mod_module.get_module()
                    loaded_modules[mod_name] = mod_instance

                # Check if the module implements an 'api' method.
                if hasattr(mod_instance, "api") and callable(getattr(mod_instance, "api")):
                    endpoint = mod_config['api_endpoint']

                    def create_api_func(module_instance):
                        """Create an API function that returns the module's API data as JSON."""
                        def api_func():
                            return jsonify(module_instance.api())
                        return api_func

                    api_func = create_api_func(mod_instance)
                    # Register the endpoint with a unique name.
                    app.add_url_rule(endpoint, endpoint + "_api", api_func)
                else:
                    print(f"Module '{mod_name}' does not implement an 'api' method; skipping API endpoint registration.")
            except Exception as e:
                print(f"Failed to register API endpoint for module '{mod_name}': {e}")


if __name__ == '__main__':
    register_api_endpoints()
    app.run(debug=True)
