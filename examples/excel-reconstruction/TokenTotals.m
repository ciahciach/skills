let
    Totals = Table.Group(SourceTokens, {"Token"}, {{"TotalUnits", each List.Sum([Units]), Int64.Type}}),
    Sorted = Table.Sort(Totals, {{"Token", Order.Ascending}})
in
    Sorted
