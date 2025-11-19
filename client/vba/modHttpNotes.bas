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
    Dim oneDriveDetected As Boolean
    Dim i As Integer
    
    Set fso = CreateObject("Scripting.FileSystemObject")
    Set wsh = CreateObject("WScript.Shell")
    
    ' Try multiple locations in order of preference
    ReDim locations(0 To 3)
    
    ' Location 1: Same directory as the presentation (if open)
    Debug.Print "DEBUG GetApiKey: Checking ActivePresentation..."
    If Not ActivePresentation Is Nothing Then
        Debug.Print "DEBUG GetApiKey: ActivePresentation is not Nothing"
        Debug.Print "DEBUG GetApiKey: ActivePresentation.Path = '" & ActivePresentation.Path & "'"
        If ActivePresentation.Path <> "" Then
            ' If path is a OneDrive/SharePoint URL, do not use it
            If Left$(ActivePresentation.Path, 7) = "http://" Or Left$(ActivePresentation.Path, 8) = "https://" Then
                Debug.Print "DEBUG GetApiKey: OneDrive/SharePoint URL detected - location 0 disabled"
                oneDriveDetected = True
                ' Leave locations(0) empty; warn later only if other locations fail
            Else
                locations(0) = ActivePresentation.Path & "\api_config.txt"
                Debug.Print "DEBUG GetApiKey: Location 0 set to: " & locations(0)
            End If
        Else
            Debug.Print "DEBUG GetApiKey: ActivePresentation.Path is empty (presentation not saved yet?)"
        End If
    Else
        Debug.Print "DEBUG GetApiKey: ActivePresentation is Nothing"
    End If
    
    ' Location 2: User's Documents folder
    locations(1) = wsh.SpecialFolders("MyDocuments") & "\XiaoiceClassAssistant\api_config.txt"
    
    ' Location 3: User's AppData\Roaming folder
    locations(2) = wsh.ExpandEnvironmentStrings("%APPDATA%") & "\XiaoiceClassAssistant\api_config.txt"
    
    ' Location 4: Temp folder (last resort)
    locations(3) = wsh.ExpandEnvironmentStrings("%TEMP%") & "\api_config.txt"
    
    ' Try each location
    For i = 0 To 3
        Debug.Print "DEBUG GetApiKey: Trying location " & i & ": " & locations(i)
        If locations(i) <> "" Then
            If fso.FileExists(locations(i)) Then
                Debug.Print "DEBUG GetApiKey: File exists at location " & i
                Set ts = fso.OpenTextFile(locations(i), 1) ' 1 = ForReading
                If Not ts.AtEndOfStream Then
                    apiKey = Trim(ts.ReadLine)
                    Debug.Print "API key loaded from: " & locations(i)
                End If
                ts.Close
                Set ts = Nothing
                If apiKey <> "" Then Exit For
            Else
                Debug.Print "DEBUG GetApiKey: File does not exist at location " & i
            End If
        Else
            Debug.Print "DEBUG GetApiKey: Location " & i & " is empty"
        End If
    Next i
    
    ' If not found in other locations and OneDrive was detected, show guidance
    If apiKey = "" And oneDriveDetected Then
        MsgBox "Your presentation is stored in OneDrive/SharePoint." & vbCrLf & vbCrLf & _
               "We couldn't find 'api_config.txt' in the supported locations." & vbCrLf & _
               "Do NOT place the key next to the OneDrive presentation." & vbCrLf & _
               "Please store your API key in one of these locations:" & vbCrLf & _
               "  • " & wsh.SpecialFolders("MyDocuments") & "\XiaoiceClassAssistant\api_config.txt" & vbCrLf & _
               "  • Registry key: HKCU\Software\XiaoiceClassAssistant\ApiKey", _
               vbExclamation, "API key location not found"
    End If
    
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
    
    ' Load credentials and endpoint (no hard-coded URL)
    Dim apiKey As String
    apiKey = GetApiKey()
    Dim baseUrl As String
    baseUrl = GetBaseUrl(apiKey)
    
    ' Debug: Print loaded configuration
    Debug.Print "DEBUG: Base URL = " & baseUrl
    Debug.Print "DEBUG: API Key = " & Left$(apiKey, 8) & "..." ' Show only first 8 chars for security
    
    ' Validate API key
    If apiKey = "" Then
        Debug.Print "Error: No API key configured. Cannot proceed."
        Exit Sub
    End If
    
    Dim url As String
    url = baseUrl & "/api/config?key=" & apiKey
    Debug.Print "DEBUG: Full URL = " & url

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
' Endpoint configuration loader (mirrors GetApiKey pattern)
' =========================
Private Function GetBaseUrl(Optional ByVal existingApiKey As String = "") As String
    On Error Resume Next
    
    Dim baseUrl As String
    Dim configPath As String
    Dim fso As Object
    Dim ts As Object
    Dim wsh As Object
    Dim locations() As String
    Dim oneDriveDetected As Boolean
    Dim i As Integer
    
    Set fso = CreateObject("Scripting.FileSystemObject")
    Set wsh = CreateObject("WScript.Shell")
    
    ' Try multiple locations (same order as GetApiKey)
    ReDim locations(0 To 3)
    Debug.Print "DEBUG GetBaseUrl: Checking ActivePresentation..."
    If Not ActivePresentation Is Nothing Then
        Debug.Print "DEBUG GetBaseUrl: ActivePresentation is not Nothing"
        Debug.Print "DEBUG GetBaseUrl: ActivePresentation.Path = '" & ActivePresentation.Path & "'"
        If ActivePresentation.Path <> "" Then
            ' If path is a OneDrive/SharePoint URL, do not use it
            If Left$(ActivePresentation.Path, 7) = "http://" Or Left$(ActivePresentation.Path, 8) = "https://" Then
                Debug.Print "DEBUG GetBaseUrl: OneDrive/SharePoint URL detected - location 0 disabled"
                oneDriveDetected = True
                ' Leave locations(0) empty; warn later only if other locations fail
            Else
                locations(0) = ActivePresentation.Path & "\api_config.txt"
                Debug.Print "DEBUG GetBaseUrl: Location 0 set to: " & locations(0)
            End If
        Else
            Debug.Print "DEBUG GetBaseUrl: ActivePresentation.Path is empty (presentation not saved yet?)"
        End If
    Else
        Debug.Print "DEBUG GetBaseUrl: ActivePresentation is Nothing"
    End If
    locations(1) = wsh.SpecialFolders("MyDocuments") & "\XiaoiceClassAssistant\api_config.txt"
    locations(2) = wsh.ExpandEnvironmentStrings("%APPDATA%") & "\XiaoiceClassAssistant\api_config.txt"
    locations(3) = wsh.ExpandEnvironmentStrings("%TEMP%") & "\api_config.txt"
    
    ' Read second line (first line is API key) if present
    For i = 0 To 3
        Debug.Print "DEBUG GetBaseUrl: Trying location " & i & ": " & locations(i)
        If locations(i) <> "" Then
            If fso.FileExists(locations(i)) Then
                Debug.Print "DEBUG GetBaseUrl: File exists at location " & i
                Set ts = fso.OpenTextFile(locations(i), 1)
                If Not ts.AtEndOfStream Then
                    Dim firstLine As String
                    firstLine = Trim(ts.ReadLine) ' API key (ignored here)
                End If
                If Not ts.AtEndOfStream Then
                    baseUrl = Trim(ts.ReadLine)
                    Debug.Print "Base URL loaded from: " & locations(i)
                Else
                    Debug.Print "DEBUG GetBaseUrl: File has only 1 line (no base URL)"
                End If
                ts.Close
                Set ts = Nothing
                If baseUrl <> "" Then Exit For
            Else
                Debug.Print "DEBUG GetBaseUrl: File does not exist at location " & i
            End If
        Else
            Debug.Print "DEBUG GetBaseUrl: Location " & i & " is empty"
        End If
    Next i
    
    ' If not found in other locations and OneDrive was detected, show guidance
    If baseUrl = "" And oneDriveDetected Then
        MsgBox "Your presentation is stored in OneDrive/SharePoint." & vbCrLf & vbCrLf & _
               "We couldn't find 'api_config.txt' with a Base URL in the supported locations." & vbCrLf & _
               "Do NOT place the file next to the OneDrive presentation." & vbCrLf & _
               "Please store your config in one of these locations:" & vbCrLf & _
               "  • " & wsh.SpecialFolders("MyDocuments") & "\XiaoiceClassAssistant\api_config.txt (2 lines: API key then Base URL)" & vbCrLf & _
               "  • Registry key: HKCU\Software\XiaoiceClassAssistant\BaseUrl", _
               vbExclamation, "Base URL location not found"
    End If
    Set fso = Nothing
    
    ' Registry fallback
    If baseUrl = "" Then
        On Error Resume Next
        baseUrl = wsh.RegRead("HKCU\Software\XiaoiceClassAssistant\BaseUrl")
        If Err.Number <> 0 Then
            baseUrl = ""
            Err.Clear
        End If
        If baseUrl <> "" Then Debug.Print "Base URL loaded from registry"
        On Error GoTo 0
    End If
    
    ' Prompt user if still empty
    If baseUrl = "" Then
        Debug.Print "DEBUG GetBaseUrl: Base URL not found - prompting user"
        On Error Resume Next
        baseUrl = InputBox("Enter the API Base URL for Xiaoice Class Assistant:" & vbCrLf & vbCrLf & _
                           "Example: https://your-gateway-id.ue.gateway.dev" & vbCrLf & _
                           "It will be saved alongside your API key.", _
                           "API Base URL Required", "")
        If Err.Number <> 0 Then
            Debug.Print "DEBUG GetBaseUrl: InputBox error: " & Err.Description
            Err.Clear
        End If
        On Error GoTo 0
        
        Debug.Print "DEBUG GetBaseUrl: User entered: '" & baseUrl & "'"
        Debug.Print "DEBUG GetBaseUrl: User entered: '" & baseUrl & "'"
        
        If baseUrl <> "" Then
            ' Remove trailing slash if present
            If Right$(baseUrl, 1) = "/" Then
                baseUrl = Left$(baseUrl, Len(baseUrl) - 1)
                Debug.Print "DEBUG GetBaseUrl: Removed trailing slash: '" & baseUrl & "'"
            End If
            
            On Error Resume Next
            ' Persist to registry
            wsh.RegWrite "HKCU\Software\XiaoiceClassAssistant\BaseUrl", baseUrl, "REG_SZ"
            If Err.Number <> 0 Then
                Debug.Print "DEBUG GetBaseUrl: Registry write error: " & Err.Description
                Err.Clear
            Else
                Debug.Print "DEBUG GetBaseUrl: Base URL saved to registry"
            End If
            
            ' Persist to file (two-line format: API key then base URL)
            Dim saveFolder As String
            saveFolder = wsh.SpecialFolders("MyDocuments") & "\XiaoiceClassAssistant"
            Set fso = CreateObject("Scripting.FileSystemObject")
            If Not fso.FolderExists(saveFolder) Then
                fso.CreateFolder saveFolder
                If Err.Number <> 0 Then
                    Debug.Print "DEBUG GetBaseUrl: Folder creation error: " & Err.Description
                    Err.Clear
                End If
            End If
            
            ' Read existing API key if file exists
            Dim existingKey As String
            existingKey = existingApiKey
            If existingKey = "" And fso.FileExists(saveFolder & "\api_config.txt") Then
                Set ts = fso.OpenTextFile(saveFolder & "\api_config.txt", 1)
                If Not ts.AtEndOfStream Then
                    existingKey = Trim(ts.ReadLine)
                End If
                ts.Close
                Set ts = Nothing
            End If
            
            Set ts = fso.CreateTextFile(saveFolder & "\api_config.txt", True)
            ' Preserve existing API key if available
            ts.WriteLine existingKey
            ts.WriteLine baseUrl
            ts.Close
            Set ts = Nothing
            Set fso = Nothing
            If Err.Number <> 0 Then
                Debug.Print "DEBUG GetBaseUrl: File save error: " & Err.Description
                Err.Clear
            Else
                Debug.Print "Base URL saved to: " & saveFolder & "\api_config.txt"
            End If
            On Error GoTo 0
        Else
            Debug.Print "DEBUG GetBaseUrl: User cancelled or entered empty URL"
        End If
    End If
    
    ' Final validation
    If baseUrl = "" Then
        Debug.Print "WARNING GetBaseUrl: Base URL is still empty - API calls will fail"
    End If
    
    Set wsh = Nothing
    GetBaseUrl = baseUrl
    If Err.Number <> 0 Then Err.Clear
End Function

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


