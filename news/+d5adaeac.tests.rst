Fixed the extends-cache unit tests building a malformed ``file://`` URL on Windows (``file://C:/...`` parses to an empty path); they now use ``Path.as_uri()``. [gotcha]
