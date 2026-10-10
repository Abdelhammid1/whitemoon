"""Generic system-settings registry (T-37).

Business constants that used to be scattered magic numbers now live in one
declared registry with metadata (label, description, example, bounds) and are
read at call-time through `service.get_int` / `service.get_decimal`, so an
authorised admin can tune them from «إعدادات النظام» and every change is logged.
"""
