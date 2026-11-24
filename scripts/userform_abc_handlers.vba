Option Explicit

Private Sub UserForm_Initialize()
    @STATUS_OPTIONS@
End Sub

Private Sub CheckSample_Click()
    Dim quantityText As String
    Dim target As Object
    quantityText = Trim$(Me.Quantity.Value)

    If Len(Trim$(Me.SampleCode.Value)) = 0 Then
        Me.ResultText.Caption = @MISSING_CODE@
        Set target = Me.SampleCode
    ElseIf Me.SampleStatus.ListIndex < 0 Then
        Me.ResultText.Caption = @MISSING_STATUS@
        Set target = Me.SampleStatus
    ElseIf Len(quantityText) = 0 Or quantityText Like "*[!0-9]*" Or Not quantityText Like "*[1-9]*" Then
        Me.ResultText.Caption = @INVALID_QUANTITY@
        Set target = Me.Quantity
    Else
        Me.ResultText.Caption = @SUCCESS@
    End If
    If Me.Visible And Not target Is Nothing Then target.SetFocus
End Sub

Private Sub ResetSample_Click()
    Me.SampleCode.Value = ""
    Me.SampleStatus.ListIndex = -1
    Me.Quantity.Value = ""
    Me.ResultText.Caption = ""
    If Me.Visible Then Me.SampleCode.SetFocus
End Sub

Public Function RunFixture() As String
    Dim cases As Variant
    Dim scenario As Variant
    Dim i As Long
    If Me.Caption <> @FORM_CAPTION@ Then Err.Raise 513, , "Form caption"
    If Me.SampleStatus.ListCount <> @STATUS_COUNT@ Then Err.Raise 513, , "List count"
    For i = 0 To Me.SampleStatus.ListCount - 1
        If Me.SampleStatus.List(i) <> Split(@STATUS_LIST@, "|")(i) Then Err.Raise 513, , "List option"
    Next i

    cases = Array( _
        Array("missing code", " ", 0, "2", @MISSING_CODE@), _
        Array("missing status", "DEMO-01", -1, "2", @MISSING_STATUS@), _
        Array("zero", "DEMO-01", 0, "0", @INVALID_QUANTITY@), _
        Array("fraction", "DEMO-01", 0, "1.5", @INVALID_QUANTITY@), _
        Array("valid", "DEMO-01", 1, "2", @SUCCESS@))
    For Each scenario In cases
        Me.SampleCode.Value = scenario(1)
        Me.SampleStatus.ListIndex = scenario(2)
        Me.Quantity.Value = scenario(3)
        CheckSample_Click
        If Me.ResultText.Caption <> scenario(4) Then Err.Raise 513, , scenario(0)
    Next scenario

    ResetSample_Click
    If Len(Me.SampleCode.Value) <> 0 Or Me.SampleStatus.ListIndex <> -1 Or _
       Len(Me.Quantity.Value) <> 0 Or Len(Me.ResultText.Caption) <> 0 Then Err.Raise 513, , "Reset"
    RunFixture = "list options, missing code, missing status, zero, fraction, valid, reset"
End Function
