from pprint import pprint

class WidgetRegistry:
    def __init__(self):
        self.widgets = {}

    def register(self, category, name, widget):
        if category not in self.widgets:
            self.widgets[category] = {}
        self.widgets[category][name] = widget

    def get_widget(self, category, name):
        return self.widgets.get(category, {}).get(name)
    
    def print_dict(self):
        pprint(self.widgets)


