' === Standard Module: modHttpNotes ===
Option Explicit

' Hold the event sink
Public PPTEvents As CAppEvents

' =========================
' Configuration
' =========================
' Function to read API key from a config file or environment
Private Function GetApiKey() As String
    On Error Resume Next
    
    ' Option 1: Read from a text file in multiple possible locations
    Dim configPath As String
    Dim fso As Object
    Dim ts As Object
    Dim apiKey As String
    Dim wsh As Object
    Dim locations() As String
    Dim i As Integer
    
    Set fso = CreateObject("Scripting.FileSystemObject")
    Set wsh = CreateObject("WScript.Shell")
    
    ' Try multiple locations in order of preference
    ReDim locations(0 To 3)
    
    ' Location 1: Same directory as the presentation (if open)
    If Not ActivePresentation Is Nothing Then
        If ActivePresentation.Path <> "" Then
            locations(0) = ActivePresentation.Path & "\api_config.txt"
        End If
    End If
    
    ' Location 2: User's Documents folder
    locations(1) = wsh.SpecialFolders("MyDocuments") & "\XiaoiceClassAssistant\api_config.txt"
    
    ' Location 3: User's AppData\Roaming folder
    locations(2) = wsh.ExpandEnvironmentStrings("%APPDATA%") & "\XiaoiceClassAssistant\api_config.txt"
    
    ' Location 4: Temp folder (last resort)
    locations(3) = wsh.ExpandEnvironmentStrings("%TEMP%") & "\api_config.txt"
    
    ' Try each location
    For i = 0 To 3
        If locations(i) <> "" Then
            If fso.FileExists(locations(i)) Then
                Set ts = fso.OpenTextFile(locations(i), 1) ' 1 = ForReading
                If Not ts.AtEndOfStream Then
                    apiKey = Trim(ts.ReadLine)
                    Debug.Print "API key loaded from: " & locations(i)
                End If
                ts.Close
                Set ts = Nothing
                If apiKey <> "" Then Exit For
            End If
        End If
    Next i
    
    Set fso = Nothing
    
    ' Option 2: Read from Windows Registry (requires user to set it once)
    If apiKey = "" Then
        apiKey = wsh.RegRead("HKCU\Software\XiaoiceClassAssistant\ApiKey")
        If apiKey <> "" Then Debug.Print "API key loaded from registry"
    End If
    
    ' Option 3: Fallback to prompt user (first time setup)
    If apiKey = "" Then
        apiKey = InputBox("Please enter your API key for Xiaoice Class Assistant:" & vbCrLf & vbCrLf & _
                         "The key will be saved to:" & vbCrLf & _
                         wsh.SpecialFolders("MyDocuments") & "\XiaoiceClassAssistant\api_config.txt", _
                         "API Key Required", "")
        
        ' Save to both registry AND file for next time
        If apiKey <> "" Then
            On Error Resume Next
            ' Save to registry
            wsh.RegWrite "HKCU\Software\XiaoiceClassAssistant\ApiKey", apiKey, "REG_SZ"
            
            ' Save to Documents folder
            Dim saveFolder As String
            saveFolder = wsh.SpecialFolders("MyDocuments") & "\XiaoiceClassAssistant"
            Set fso = CreateObject("Scripting.FileSystemObject")
            
            ' Create folder if it doesn't exist
            If Not fso.FolderExists(saveFolder) Then
                fso.CreateFolder saveFolder
            End If
            
            ' Write the key to file
            Set ts = fso.CreateTextFile(saveFolder & "\api_config.txt", True)
            ts.WriteLine apiKey
            ts.Close
            Set ts = Nothing
            Set fso = Nothing
            
            Debug.Print "API key saved to: " & saveFolder & "\api_config.txt"
        End If
    End If
    
    Set wsh = Nothing
    GetApiKey = apiKey
    If Err.Number <> 0 Then Err.Clear
End Function

' =========================
' Session init / teardown
' =========================
Public Sub InitSlideShowEvents()
    On Error GoTo EH
    Set PPTEvents = New CAppEvents
    Set PPTEvents.PPTEvent = Application
    Debug.Print "? Slide show event handler initialized."
    Exit Sub
EH:
    Debug.Print "? InitSlideShowEvents error: "; Err.Number; " - "; Err.Description
End Sub

Public Sub StopSlideShowEvents()
    On Error Resume Next
    Set PPTEvents.PPTEvent = Nothing
    Set PPTEvents = Nothing
    Debug.Print "? Slide show event handler stopped."
End Sub

' =========================
' Notes extraction
' =========================
' Returns all text found on the Notes Page of a given slide
Public Function GetNotesText(ByVal sld As Slide) As String
    Dim shp As Shape
    Dim notesText As String
    notesText = ""

    ' Loop all shapes on the Notes Page, collecting text
    For Each shp In sld.NotesPage.Shapes
        If shp.HasTextFrame Then
            If shp.TextFrame.HasText Then
                notesText = notesText & shp.TextFrame.TextRange.Text & vbCrLf
            End If
        End If
    Next shp

    ' Trim trailing CRLF
    If Len(notesText) > 1 Then
        If Right$(notesText, 2) = vbCrLf Then
            notesText = Left$(notesText, Len(notesText) - 2)
        End If
    End If

    GetNotesText = notesText
End Function

' =========================
' Main entry (called by event)
' =========================
Public Sub SetPresentation(ByVal presentation As String)
    On Error Resume Next
    
    ' -- Configure your endpoint here --
    Dim baseUrl As String
    baseUrl = "https://gateway-25iq0pr1.ue.gateway.dev"
    Dim apiKey As String
    apiKey = GetApiKey()
    
    ' Validate API key
    If apiKey = "" Then
        Debug.Print "Error: No API key configured. Cannot proceed."
        Exit Sub
    End If
    
    Dim url As String
    url = baseUrl & "/api/config?key=" & apiKey

    ' Prepare payload
    Dim bodyString As String
    bodyString = BuildConfigPayloadWithGeneration(presentation)

    ' Attempt HTTP request with fallback methods
    Dim statusCode As Long
    Dim responseText As String
    statusCode = 0
    responseText = ""
    
    ' Try WinHTTP (most reliable in Office)
    PostJsonWinHttp url, bodyString, statusCode, responseText
    If Err.Number <> 0 Then Err.Clear
    
    ' Fallback to ServerXMLHTTP
    If statusCode = 0 Then
        PostJsonXmlHttp url, bodyString, statusCode, responseText
        If Err.Number <> 0 Then Err.Clear
    End If
    
    ' Final fallback to legacy XMLHTTP
    If statusCode = 0 Then
        PostJsonXmlHttpLegacy url, bodyString, statusCode, responseText
        If Err.Number <> 0 Then Err.Clear
    End If

    ' Handle response
    If statusCode = 200 Then
        Debug.Print "Config updated successfully"
    ElseIf statusCode = 0 Then
        Debug.Print "HTTP request failed. Check macro security settings or run PowerPoint as Administrator."
    Else
        Debug.Print "Config update failed. HTTP Status: " & statusCode
    End If
    
    If Err.Number <> 0 Then Err.Clear
End Sub

' =========================
' HTTP helpers
' =========================

' -- ServerXMLHTTP method (Often blocked by security) --
Private Sub PostJsonXmlHttp(ByVal url As String, ByVal bodyString As String, _
                            ByRef statusCode As Long, ByRef responseText As String)
    On Error Resume Next
    
    Dim xhr As Object
    Set xhr = CreateObject("MSXML2.ServerXMLHTTP.6.0")
    
    ' Check if CreateObject failed
    If Err.Number <> 0 Or xhr Is Nothing Then
        statusCode = 0
        responseText = ""
        Exit Sub
    End If

    xhr.Open "POST", url, False
    If Err.Number <> 0 Then
        statusCode = 0
        responseText = ""
        Exit Sub
    End If
    
    xhr.SetRequestHeader "Content-Type", "application/json; charset=utf-8"
    xhr.SetRequestHeader "User-Agent", "PowerPoint-VBA/1.0"

    xhr.Send bodyString
    If Err.Number <> 0 Then
        statusCode = 0
        responseText = ""
        Exit Sub
    End If

    statusCode = xhr.status
    responseText = xhr.responseText
End Sub

' -- Legacy MSXML2.XMLHTTP (No server restrictions) --
Private Sub PostJsonXmlHttpLegacy(ByVal url As String, ByVal bodyString As String, _
                                  ByRef statusCode As Long, ByRef responseText As String)
    On Error Resume Next
    
    Dim xhr As Object
    Set xhr = CreateObject("MSXML2.XMLHTTP")
    
    ' Check if CreateObject failed
    If Err.Number <> 0 Or xhr Is Nothing Then
        statusCode = 0
        responseText = ""
        Exit Sub
    End If

    xhr.Open "POST", url, False
    If Err.Number <> 0 Then
        statusCode = 0
        responseText = ""
        Exit Sub
    End If
    
    xhr.SetRequestHeader "Content-Type", "application/json; charset=utf-8"
    xhr.SetRequestHeader "User-Agent", "PowerPoint-VBA/1.0"

    xhr.Send bodyString
    If Err.Number <> 0 Then
        statusCode = 0
        responseText = ""
        Exit Sub
    End If

    statusCode = xhr.status
    responseText = xhr.responseText
End Sub

' -- Fallback: WinHttp.WinHttpRequest.5.1 (Known to be reliable) --
Private Sub PostJsonWinHttp(ByVal url As String, ByVal bodyString As String, _
                            ByRef statusCode As Long, ByRef responseText As String)
    On Error Resume Next
    
    Dim http As Object
    Set http = CreateObject("WinHttp.WinHttpRequest.5.1")
    
    ' Check if CreateObject failed
    If Err.Number <> 0 Or http Is Nothing Then
        statusCode = 0
        responseText = ""
        Exit Sub
    End If

    ' Timeouts: Resolve, Connect, Send, Receive (ms)
    http.SetTimeouts 10000, 10000, 30000, 30000
    If Err.Number <> 0 Then
        statusCode = 0
        responseText = ""
        Exit Sub
    End If

    http.Open "POST", url, False
    If Err.Number <> 0 Then
        statusCode = 0
        responseText = ""
        Exit Sub
    End If
    
    http.SetRequestHeader "Content-Type", "application/json; charset=utf-8"
    http.SetRequestHeader "User-Agent", "PowerPoint-VBA/1.0"

    ' Send as string - more compatible
    http.Send bodyString
    If Err.Number <> 0 Then
        statusCode = 0
        responseText = ""
        Exit Sub
    End If

    statusCode = http.status
    responseText = http.responseText
End Sub

' =========================
' JSON & encoding helpers
' =========================

' Build payload for agent-generated presentation messages
Private Function BuildConfigPayloadWithGeneration(ByVal context As String) As String
    Dim json As String
    json = _
        "{" & _
          """generate_presentation"":true," & _
          """languages"":[""en"",""zh""]," & _
          """context"":""" & JsonEscape(context) & """," & _
          """presentation_messages"":{}," & _
          """welcome_messages"":{}," & _
          """goodbye_messages"":{}" & _
        "}"
    BuildConfigPayloadWithGeneration = json
End Function

' Build compact JSON (no extra spaces/newlines).
Private Function BuildConfigPayload(ByVal testPresentation As String, _
                                      ByVal testGoodbye As String, _
                                      ByVal testQuestion As String, _
                                      ByVal testTalk As String) As String
    
    ' Define escaped static strings - FIXED Chinese encoding
    Dim escapedQues2En As String
    Dim escapedQues2Zh As String

    escapedQues2En = JsonEscape("What else can you do?")
    ' Chinese: "What else can you do?"
    escapedQues2Zh = JsonEscape(ChrW(&H4F60) & ChrW(&H8FD8) & ChrW(&H80FD) & ChrW(&H505A) & ChrW(&H4EC0) & ChrW(&H4E48) & ChrW(&HFF1F))

    Dim json As String
    json = _
        "{" & _
          """presentation_messages"":{" & _
            """en"":""" & JsonEscape(testPresentation) & """," & _
            """zh"":""" & JsonEscape(testPresentation) & """" & _
          "}," & _
          """goodbye_messages"":{" & _
            """en"":""" & JsonEscape(testGoodbye) & """," & _
            """zh"":""" & JsonEscape(testGoodbye) & """" & _
          "}," & _
          """recommended_questions"":{" & _
            """en"":[""" & JsonEscape(testQuestion) & """,""" & escapedQues2En & """]," & _
            """zh"":[""" & JsonEscape(testQuestion) & """,""" & escapedQues2Zh & """]" & _
          "}," & _
          """talk_responses"":{" & _
            """en"":""" & JsonEscape(testTalk) & """," & _
            """zh"":""" & JsonEscape(testTalk) & """" & _
          "}" & _
        "}"
        
    BuildConfigPayload = json
End Function

' Minimal JSON string escaper (handles backslash and quote)
Private Function JsonEscape(ByVal s As String) As String
    Dim t As String
    t = Replace$(s, "\", "\\")
    t = Replace$(t, """", "\""")
    ' Also handle common control characters
    t = Replace$(t, vbCr, "\r")
    t = Replace$(t, vbLf, "\n")
    t = Replace$(t, vbTab, "\t")
    JsonEscape = t
End Function

' =========================
' Misc helpers
' =========================

' Returns an 8+ char random token derived from a GUID
Private Function MakeRandomId8() As String
    Dim guid As String
    guid = CreateObject("Scriptlet.TypeLib").guid
    guid = Replace$(guid, "{", "")
    guid = Replace$(guid, "}", "")
    guid = Replace$(guid, "-", "")
    MakeRandomId8 = guid
End Function

' UNIX epoch time in milliseconds (LOCAL time). Use only if your API expects local time.
Private Function EpochMillisLocal() As Double
    ' DateDiff returns seconds; multiply by 1000# (Double) to avoid overflow
    EpochMillisLocal = CDbl(DateDiff("s", #1/1/1970#, Now)) * 1000#
End Function

' Simple UTF-8 encoder for typical BMP characters (ASCII + common CJK handled)
' Avoids ADODB.Stream to reduce "Permission denied" risk.
Private Function ToUtf8Bytes(ByVal s As String) As Byte()
    Dim i As Long, ch As Long
    Dim bytes() As Byte
    Dim idx As Long

    ReDim bytes(0 To 0)
    idx = -1

    For i = 1 To Len(s)
        ch = AscW(Mid$(s, i, 1))
        If ch < &H80 Then
            ' 1-byte ASCII
            idx = idx + 1: ReDim Preserve bytes(0 To idx)
            bytes(idx) = ch And &H7F&
        ElseIf ch < &H800 Then
            ' 2-byte sequence
            idx = idx + 2: ReDim Preserve bytes(0 To idx)
            bytes(idx - 1) = &HC0 Or (ch \ &H40)
            bytes(idx) = &H80 Or (ch And &H3F)
        Else
            ' 3-byte sequence (covers most BMP characters including Chinese)
            idx = idx + 3: ReDim Preserve bytes(0 To idx)
            bytes(idx - 2) = &HE0 Or (ch \ &H1000)
            bytes(idx - 1) = &H80 Or ((ch \ &H40) And &H3F)
            bytes(idx) = &H80 Or (ch And &H3F)
        End If
    Next i

    ToUtf8Bytes = bytes
End Function

' =========================
' Smoke test you can run from the Immediate Window
' =========================
Public Sub SmokeTest()
    Dim status As Long, resp As String
    Dim body As String
    body = "{""ping"":""pong""}"
     
    Debug.Print "Running SmokeTest with ServerXMLHTTP..."
    PostJsonXmlHttp "https://httpbin.org/post", body, status, resp
    Debug.Print "Status=", status
    Debug.Print resp

    If status = 0 Then
        Debug.Print "Trying WinHTTP fallback..."
        PostJsonWinHttp "https://httpbin.org/post", body, status, resp
        Debug.Print "WinHTTP Status=", status
        Debug.Print resp
    End If
End Sub


