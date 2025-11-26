'=== Class Module: CAppEvents ===
Option Explicit

' Declare the application variable as Private to handle events internally
Private WithEvents mPPTEvent As Application

' Expose a Public Property to set the Application object from the Module
Public Property Set PPTEvent(ByVal Value As Application)
    Set mPPTEvent = Value
End Property

Public Property Get PPTEvent() As Application
    Set PPTEvent = mPPTEvent
End Property

' ===================================
' Event: SlideShowBegin
' FIX: Fires when the slideshow starts (i.e., when the first slide is shown).
' ===================================
Private Sub mPPTEvent_SlideShowBegin(ByVal Wn As SlideShowWindow)
    On Error GoTo EH

    Dim currentNotes As String
    
    ' Get the slide object for the currently displayed slide (the first one)
    currentNotes = modHttpNotes.GetNotesText(Wn.View.Slide)

    Debug.Print "=== SlideShowBegin ==="
    Debug.Print "Current slide position: " & Wn.View.CurrentShowPosition
    Debug.Print "Notes length: " & Len(currentNotes) & " chars"
    Debug.Print "Notes content: " & Left$(currentNotes, 100) & IIf(Len(currentNotes) > 100, "...", "")

    If Len(Trim$(currentNotes)) = 0 Then
        Debug.Print "WARNING: No notes on this slide"
    Else
        ' Call into the standard module to send the HTTP request
        Debug.Print "Calling SetWelcome..."
        modHttpNotes.SetWelcome currentNotes
    End If

    Exit Sub
EH:
    Debug.Print "? PPTEvent_SlideShowBegin error: "; Err.Number; " - "; Err.Description
End Sub


' ===================================
' Event: SlideShowNextSlide
' Fires when moving to the 2nd slide and every slide thereafter.
' ===================================
Private Sub mPPTEvent_SlideShowNextSlide(ByVal Wn As SlideShowWindow)
    On Error GoTo EH

    Dim currentNotes As String
    currentNotes = modHttpNotes.GetNotesText(Wn.View.Slide)

    Debug.Print "=== SlideShowNextSlide ==="
    Debug.Print "Current slide position: " & Wn.View.CurrentShowPosition
    Debug.Print "Notes length: " & Len(currentNotes) & " chars"
    Debug.Print "Notes content: " & Left$(currentNotes, 100) & IIf(Len(currentNotes) > 100, "...", "")

    If Len(Trim$(currentNotes)) = 0 Then
        Debug.Print "WARNING: No notes on this slide"
    Else
        ' Call into the standard module to send the HTTP request
        Debug.Print "Calling SetWelcome..."
        modHttpNotes.SetWelcome currentNotes
    End If

    Exit Sub
EH:
    Debug.Print "? PPTEvent_SlideShowNextSlide error: "; Err.Number; " - "; Err.Description
End Sub