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
    If Not ActivePresentation Is Nothing Then
        If ActivePresentation.Path <> "" Then
            ' If path is a OneDrive/SharePoint URL, do not use it
            If Left$(ActivePresentation.Path, 7) = "http://" Or Left$(ActivePresentation.Path, 8) = "https://" Then
                oneDriveDetected = True
                ' Leave locations(0) empty; warn later only if other locations fail
            Else
                locations(0) = ActivePresentation.Path & "\api_config.txt"
            End If
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
                End If
                ts.Close
                Set ts = Nothing
                If apiKey <> "" Then Exit For
            End If
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
    Exit Sub
EH:
    ' Event handler initialization failed
End Sub

Public Sub StopSlideShowEvents()
    On Error Resume Next
    Set PPTEvents.PPTEvent = Nothing
    Set PPTEvents = Nothing
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

' Extract speaker notes from all slides and combine them
Public Function GetAllSpeakerNotes() As String
    On Error Resume Next
    Dim sld As Slide
    Dim allNotes As String
    Dim slideNum As Integer
    
    allNotes = ""
    slideNum = 0
    
    ' Loop through all slides in the active presentation
    If Not ActivePresentation Is Nothing Then
        For Each sld In ActivePresentation.Slides
            slideNum = slideNum + 1
            Dim notes As String
            notes = GetNotesText(sld)
            If notes <> "" Then
                If allNotes <> "" Then
                    allNotes = allNotes & vbCrLf & vbCrLf
                End If
                allNotes = allNotes & "Slide " & slideNum & ": " & notes
            End If
        Next sld
    End If
    
    ' If no notes found, return empty string
    GetAllSpeakerNotes = allNotes
End Function

' Extract slide number from presentation string (e.g., "slide3" -> "3")
Private Function ExtractSlideNumber(ByVal presentation As String) As String
    On Error Resume Next
    Dim slideNum As String
    
    ' If presentation contains "slide" followed by number
    If InStr(1, LCase(presentation), "slide") > 0 Then
        ' Extract the number after "slide"
        Dim pos As Integer
        pos = InStr(1, LCase(presentation), "slide")
        If pos > 0 Then
            slideNum = Mid(presentation, pos + 5) ' Skip "slide"
            ' Extract only digits
            Dim i As Integer
            Dim numStr As String
            numStr = ""
            For i = 1 To Len(slideNum)
                If IsNumeric(Mid(slideNum, i, 1)) Then
                    numStr = numStr & Mid(slideNum, i, 1)
                Else
                    Exit For
                End If
            Next i
            slideNum = numStr
        End If
    End If
    
    ' Default to slide 1 if not found
    If slideNum = "" Or Not IsNumeric(slideNum) Then
        slideNum = "1"
    End If
    
    ExtractSlideNumber = slideNum
End Function

' Get notes for a specific slide number
Private Function GetCurrentSlideNotes(ByVal slideNum As String) As String
    On Error Resume Next
    Dim sldIndex As Integer
    sldIndex = CInt(slideNum)
    
    If sldIndex < 1 Or ActivePresentation Is Nothing Then
        GetCurrentSlideNotes = ""
        Exit Function
    End If
    
    If sldIndex > ActivePresentation.Slides.Count Then
        GetCurrentSlideNotes = ""
        Exit Function
    End If
    
    GetCurrentSlideNotes = GetNotesText(ActivePresentation.Slides(sldIndex))
End Function

' =========================
' Main entry (called by event)
' =========================
Public Sub SetWelcome(ByVal currentNotes As String)
    ' This function is called by the event handlers with the current slide notes
    ' We need to determine which slide we're on from the SlideShow window
    On Error Resume Next
    
    Dim slideNum As String
    slideNum = "1"  ' Default
    
    ' Try to get the current slide position from the active slideshow
    If Not Application.SlideShowWindows Is Nothing Then
        If Application.SlideShowWindows.Count > 0 Then
            slideNum = CStr(Application.SlideShowWindows(1).View.CurrentShowPosition)
        End If
    End If
    
    Debug.Print "Slide number: " & slideNum & ", Notes: " & currentNotes
    Debug.Print "Context/Notes content: " & currentNotes
    
    ' Load credentials and endpoint
    Dim apiKey As String
    apiKey = GetApiKey()
    Dim baseUrl As String
    baseUrl = GetBaseUrl(apiKey)
    
    ' Get Course ID if available
    Dim courseId As String
    courseId = GetCourseId()
    
    ' Validate API key
    If apiKey = "" Then
        Exit Sub
    End If
    
    Dim url As String
    url = baseUrl & "/api/config?key=" & apiKey

    ' Prepare payload with the speaker notes and course ID
    Dim bodyString As String
    bodyString = BuildConfigPayloadWithGeneration(currentNotes, courseId)

    ' Attempt HTTP request with fallback methods
    Dim statusCode As Long
    Dim responseText As String
    statusCode = 0
    responseText = ""
    
    ' Try WinHTTP (most reliable in Office)
    Debug.Print "[SetWelcome] Attempting HTTP POST to: " & url
    PostJsonWinHttp url, bodyString, statusCode, responseText
    If Err.Number <> 0 Then
        Debug.Print "[SetWelcome] WinHTTP error: " & Err.Description
        Err.Clear
    End If
    
    ' Fallback to ServerXMLHTTP
    If statusCode = 0 Then
        Debug.Print "[SetWelcome] WinHTTP failed, trying ServerXMLHTTP..."
        PostJsonXmlHttp url, bodyString, statusCode, responseText
        If Err.Number <> 0 Then
            Debug.Print "[SetWelcome] ServerXMLHTTP error: " & Err.Description
            Err.Clear
        End If
    End If
    
    ' Final fallback to legacy XMLHTTP
    If statusCode = 0 Then
        Debug.Print "[SetWelcome] ServerXMLHTTP failed, trying legacy XMLHTTP..."
        PostJsonXmlHttpLegacy url, bodyString, statusCode, responseText
        If Err.Number <> 0 Then
            Debug.Print "[SetWelcome] Legacy XMLHTTP error: " & Err.Description
            Err.Clear
        End If
    End If

    ' Handle response
    Debug.Print "[SetWelcome] HTTP Status Code: " & statusCode
    If statusCode = 200 Then
        Debug.Print "[SetWelcome] SUCCESS: Config updated"
        If Len(responseText) > 0 Then
            Debug.Print "[SetWelcome] Response (first 200 chars): " & Left$(responseText, 200)
        End If
    ElseIf statusCode = 0 Then
        Debug.Print "[SetWelcome] ERROR: All HTTP methods failed"
    Else
        Debug.Print "[SetWelcome] ERROR: HTTP " & statusCode
        If Len(responseText) > 0 Then
            Debug.Print "[SetWelcome] Response: " & Left$(responseText, 200)
        End If
    End If
    
    If Err.Number <> 0 Then Err.Clear
End Sub

Public Sub SetPresentation(ByVal presentation As String)
    On Error Resume Next
    
    ' Load credentials and endpoint (no hard-coded URL)
    Dim apiKey As String
    apiKey = GetApiKey()
    Dim baseUrl As String
    baseUrl = GetBaseUrl(apiKey)
    
    ' Get Course ID if available
    Dim courseId As String
    courseId = GetCourseId()
    
    ' Validate API key
    If apiKey = "" Then
        Exit Sub
    End If
    
    Dim url As String
    url = baseUrl & "/api/config?key=" & apiKey

    ' Note: presentation parameter contains slide info (e.g., "slide3")
    ' Extract slide number to get current slide notes
    Dim slideNum As String
    slideNum = ExtractSlideNumber(presentation)
    Debug.Print "Slide number: " & slideNum & ", Presentation param: " & presentation
    
    ' Get notes for current slide
    Dim slideNotes As String
    slideNotes = GetCurrentSlideNotes(slideNum)
    Debug.Print "Context/Notes content: " & slideNotes
    
    ' Prepare payload with just the speaker notes (no slide number)
    ' This way cache works even if slides are reordered
    Dim bodyString As String
    bodyString = BuildConfigPayloadWithGeneration(slideNotes, courseId)

    ' Attempt HTTP request with fallback methods
    Dim statusCode As Long
    Dim responseText As String
    statusCode = 0
    responseText = ""
    
    ' Try WinHTTP (most reliable in Office)
    Debug.Print "[SetPresentation] Attempting HTTP POST to: " & url
    PostJsonWinHttp url, bodyString, statusCode, responseText
    If Err.Number <> 0 Then
        Debug.Print "[SetPresentation] WinHTTP error: " & Err.Description
        Err.Clear
    End If
    
    ' Fallback to ServerXMLHTTP
    If statusCode = 0 Then
        Debug.Print "[SetPresentation] WinHTTP failed, trying ServerXMLHTTP..."
        PostJsonXmlHttp url, bodyString, statusCode, responseText
        If Err.Number <> 0 Then
            Debug.Print "[SetPresentation] ServerXMLHTTP error: " & Err.Description
            Err.Clear
        End If
    End If
    
    ' Final fallback to legacy XMLHTTP
    If statusCode = 0 Then
        Debug.Print "[SetPresentation] ServerXMLHTTP failed, trying legacy XMLHTTP..."
        PostJsonXmlHttpLegacy url, bodyString, statusCode, responseText
        If Err.Number <> 0 Then
            Debug.Print "[SetPresentation] Legacy XMLHTTP error: " & Err.Description
            Err.Clear
        End If
    End If

    ' Handle response
    Debug.Print "[SetPresentation] HTTP Status Code: " & statusCode
    If statusCode = 200 Then
        Debug.Print "[SetPresentation] SUCCESS: Config updated"
        If Len(responseText) > 0 Then
            Debug.Print "[SetPresentation] Response (first 200 chars): " & Left$(responseText, 200)
        End If
    ElseIf statusCode = 0 Then
        Debug.Print "[SetPresentation] ERROR: All HTTP methods failed"
    Else
        Debug.Print "[SetPresentation] ERROR: HTTP " & statusCode
        If Len(responseText) > 0 Then
            Debug.Print "[SetPresentation] Response: " & Left$(responseText, 200)
        End If
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
    If Not ActivePresentation Is Nothing Then
        If ActivePresentation.Path <> "" Then
            ' If path is a OneDrive/SharePoint URL, do not use it
            If Left$(ActivePresentation.Path, 7) = "http://" Or Left$(ActivePresentation.Path, 8) = "https://" Then
                oneDriveDetected = True
                ' Leave locations(0) empty; warn later only if other locations fail
            Else
                locations(0) = ActivePresentation.Path & "\api_config.txt"
            End If
        End If
    End If
    locations(1) = wsh.SpecialFolders("MyDocuments") & "\XiaoiceClassAssistant\api_config.txt"
    locations(2) = wsh.ExpandEnvironmentStrings("%APPDATA%") & "\XiaoiceClassAssistant\api_config.txt"
    locations(3) = wsh.ExpandEnvironmentStrings("%TEMP%") & "\api_config.txt"
    
    ' Read second line (first line is API key) if present
    For i = 0 To 3
        If locations(i) <> "" Then
            If fso.FileExists(locations(i)) Then
                Set ts = fso.OpenTextFile(locations(i), 1)
                If Not ts.AtEndOfStream Then
                    Dim firstLine As String
                    firstLine = Trim(ts.ReadLine) ' API key (ignored here)
                End If
                If Not ts.AtEndOfStream Then
                    baseUrl = Trim(ts.ReadLine)
                End If
                ts.Close
                Set ts = Nothing
                If baseUrl <> "" Then Exit For
            End If
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
        On Error GoTo 0
    End If
    
    ' Prompt user if still empty
    If baseUrl = "" Then
        On Error Resume Next
        baseUrl = InputBox("Enter the API Base URL for Xiaoice Class Assistant:" & vbCrLf & vbCrLf & _
                           "Example: https://your-gateway-id.ue.gateway.dev" & vbCrLf & _
                           "It will be saved alongside your API key.", _
                           "API Base URL Required", "")
        If Err.Number <> 0 Then
            Err.Clear
        End If
        On Error GoTo 0
        
        If baseUrl <> "" Then
            ' Remove trailing slash if present
            If Right$(baseUrl, 1) = "/" Then
                baseUrl = Left$(baseUrl, Len(baseUrl) - 1)
            End If
            
            On Error Resume Next
            ' Persist to registry
            wsh.RegWrite "HKCU\Software\XiaoiceClassAssistant\BaseUrl", baseUrl, "REG_SZ"
            If Err.Number <> 0 Then
                Err.Clear
            End If
            
            ' Persist to file (two-line format: API key then base URL)
            Dim saveFolder As String
            saveFolder = wsh.SpecialFolders("MyDocuments") & "\XiaoiceClassAssistant"
            Set fso = CreateObject("Scripting.FileSystemObject")
            If Not fso.FolderExists(saveFolder) Then
                fso.CreateFolder saveFolder
                If Err.Number <> 0 Then
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
                Err.Clear
            End If
            On Error GoTo 0
        End If
    End If
    
    Set wsh = Nothing
    GetBaseUrl = baseUrl
    If Err.Number <> 0 Then Err.Clear
End Function

' =========================
' Course ID Configuration loader (similar pattern)
' =========================
Private Function GetCourseId() As String
    On Error Resume Next
    
    Dim courseId As String
    Dim configPath As String
    Dim fso As Object
    Dim ts As Object
    Dim wsh As Object
    Dim locations() As String
    Dim i As Integer
    
    Set fso = CreateObject("Scripting.FileSystemObject")
    Set wsh = CreateObject("WScript.Shell")
    
    ' Try multiple locations (same order as GetApiKey)
    ReDim locations(0 To 3)
    If Not ActivePresentation Is Nothing Then
        If ActivePresentation.Path <> "" Then
            If Left$(ActivePresentation.Path, 7) <> "http://" And Left$(ActivePresentation.Path, 8) <> "https://" Then
                locations(0) = ActivePresentation.Path & "\api_config.txt"
            End If
        End If
    End If
    locations(1) = wsh.SpecialFolders("MyDocuments") & "\XiaoiceClassAssistant\api_config.txt"
    locations(2) = wsh.ExpandEnvironmentStrings("%APPDATA%") & "\XiaoiceClassAssistant\api_config.txt"
    locations(3) = wsh.ExpandEnvironmentStrings("%TEMP%") & "\api_config.txt"
    
    ' Read third line (Key, URL, CourseID)
    For i = 0 To 3
        If locations(i) <> "" Then
            If fso.FileExists(locations(i)) Then
                Set ts = fso.OpenTextFile(locations(i), 1)
                ' Skip line 1 (Key)
                If Not ts.AtEndOfStream Then ts.SkipLine
                ' Skip line 2 (URL)
                If Not ts.AtEndOfStream Then ts.SkipLine
                ' Read line 3 (CourseID)
                If Not ts.AtEndOfStream Then
                    courseId = Trim(ts.ReadLine)
                End If
                ts.Close
                Set ts = Nothing
                If courseId <> "" Then Exit For
            End If
        End If
    Next i
    
    Set fso = Nothing
    
    ' Registry fallback
    If courseId = "" Then
        On Error Resume Next
        courseId = wsh.RegRead("HKCU\Software\XiaoiceClassAssistant\CourseId")
        If Err.Number <> 0 Then
            courseId = ""
            Err.Clear
        End If
        On Error GoTo 0
    End If
    
    Set wsh = Nothing
    GetCourseId = courseId
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
Private Function BuildConfigPayloadWithGeneration(ByVal context As String, Optional ByVal courseId As String = "") As String
    Dim json As String
    
    ' If courseId is provided, use it (backend handles languages from course config)
    ' If not, fallback to legacy behavior with default languages
    Dim courseConfig As String
    If courseId <> "" Then
        courseConfig = """courseId"":""" & JsonEscape(courseId) & ""","
    Else
        courseConfig = """languages"":[""en"",""zh""],"
    End If
    
    json = _
        "{" & _
          """generate_presentation"":true," & _
          courseConfig & _
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
     
    Debug.Print "=== Smoke Test ==="
    Debug.Print "Testing ServerXMLHTTP..."
    PostJsonXmlHttp "https://httpbin.org/post", body, status, resp
    Debug.Print "Status: " & status
    If status > 0 Then
        Debug.Print "Response (first 500 chars): " & Left$(resp, 500)
    Else
        Debug.Print "ServerXMLHTTP failed, trying WinHTTP..."
        PostJsonWinHttp "https://httpbin.org/post", body, status, resp
        Debug.Print "Status: " & status
        If status > 0 Then
            Debug.Print "Response (first 500 chars): " & Left$(resp, 500)
        Else
            Debug.Print "ERROR: Both methods failed"
        End If
    End If
    Debug.Print "=== Test Complete ==="
End Sub




