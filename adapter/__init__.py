"""M12: agent-facing adapter a Rover Gateway-hez.

Retegek:
- backend.py: a rover backend absztrakcioja (Unity TCP / mock), v1 protokoll
- orseg.py:   biztonsagi reteg - parameter-validacio a backend ELOTT,
              session-limitek, automatikus stop, backend-rejtes
- mcp_szerver.py: MCP-szerver, ami csak a szukseges eszkozoket teszi ki
"""
