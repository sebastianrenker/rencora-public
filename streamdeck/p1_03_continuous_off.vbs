Set h = CreateObject("MSXML2.XMLHTTP")
On Error Resume Next
h.Open "GET", "http://localhost:8000/api/sd?do=continuous_off", False
h.Send
