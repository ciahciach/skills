let
    Source = Excel.CurrentWorkbook(){[Name = "tblTokens"]}[Content],
    WithoutBlankRows = Table.SelectRows(Source, each [Token] <> null or [Units] <> null),
    Typed = Table.TransformColumnTypes(WithoutBlankRows, {{"Token", type text}, {"Units", Int64.Type}}, "en-US")
in
    Typed
