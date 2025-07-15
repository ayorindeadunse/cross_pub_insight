import textwrap

def review_before_summary(state: dict) -> dict:
    print("\n===== HUMAN-IN-THE-LOOP: REVIEW BEFORE FINAL SUMMARY =====")
    print("\n Analysis Result:\n")
    print(textwrap.fill(state.get("analysis_result", ""), width=100))

    print("\n Detected Trends:\n")
    print(textwrap.fill(state.get("aggregated_trends", ""), width=100))

    print("\n Fact Check Feedback:\n")
    print(textwrap.fill(state.get("fact_check_result", ""), width=100))

    print("\nWould you like to edit the analysis before summarization?")
    choice= input("Enter [e]dit, [c]ontinue, or [s]kip summarization: ").strip().lower()

    if choice == "e":
        print("\nPaste your updated analysis below (end input with an empty line):")
        lines = []
        while True:
            line = input()
            if not line.strip():
                break
            lines.append(line)
        edited = "\n".join(lines).strip()
        if edited:
            state["analysis_result"] = edited
            print(" Analysis updated.")
    
    elif choice == "s":
        print("Skipping summarization as requested.")
        state["final_summary"] = "Summarization skipped by human operator."
    
    else:
        print("Continuing without changes.")
    
    return state