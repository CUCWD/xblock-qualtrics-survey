import pkg_resources

def resource_string(path):
    """
    Handy helper for getting resources from our kit.

    This loads the data from a local `path` file.
    Used when loading `/static` CSS and Javascript file contents directory on page.

    Needed to define this here instead of where the `student_view()` is because
    the `__name__` value and the path needs to resolve to `/static` path.
    """
    data = pkg_resources.resource_string(__name__, path)
    return data.decode("utf8")
