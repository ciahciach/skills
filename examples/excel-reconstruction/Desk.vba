Option Explicit

Private Sub Worksheet_Change(ByVal Target As Range)
    If Application.Intersect(Target, Me.Range("B1")) Is Nothing Then Exit Sub
    Me.Range("E2").Value2 = "Pending"
End Sub
