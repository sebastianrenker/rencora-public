Set h = CreateObject("MSXML2.XMLHTTP")
On Error Resume Next
h.Open "GET", "http://localhost:8000/api/sd?do=open_status", False
h.Send
