from qdrant_client.models import Filter, FieldCondition, MatchAny

def build_qdrant_filter(search_mode: str, target_files: list[str]) -> Filter | None:
    """
    Builds a Qdrant Payload filter based on the Streamlit UI Search Mode.
    If mode is 'Global Drive Search' or no files are targeted, it returns None (no filter).
    If mode is 'Contextual Search', it builds a filter to only match chunks from the selected files.
    """
    if "global" in search_mode.lower():
        return None
        
    # If Contextual Search but NO files selected, create an impossible filter
    if not target_files:
        return Filter(
            must=[
                FieldCondition(
                    key="file_name",
                    match=MatchAny(any=["__IMPOSSIBLE_EMPTY_MATCH__"])
                )
            ]
        )
        
    return Filter(
        must=[
            FieldCondition(
                key="file_name",
                match=MatchAny(any=target_files)
            )
        ]
    )
