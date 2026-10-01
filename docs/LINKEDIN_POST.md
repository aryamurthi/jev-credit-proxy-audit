# Suggested LinkedIn post

I tested whether a ZIP code moves an AI decision model's credit decisions. For three ZIPs in one region, which ZIP it was made no measurable difference. How I checked is the useful part.

I took TypeSafe's Jev, a model that picks between options and reports a probability for each, and asked it to triage 1,000 synthetic credit applications: approve, send to a human, or deny.

Then I changed one thing at a time while keeping every financial field identical:
- added a ZIP code (three ZIPs, picked in advance from Census data to contrast race and income)
- added a meaningless label ("Internal batch: B17")
- changed the debt-to-income ratio by 20 points

Average change in the approval probability:
- same request sent again: 0.3 points
- meaningless label: 1.2 points
- any of the three ZIPs: 1.0 point
- debt-to-income change: 13.3 points

Which of the three ZIPs made no measurable difference (about 0.02 points between them). Adding any ZIP nudged strong applicants down about a point and borderline ones up about a point. In a second run with an instruction to ignore geography, the wobble from any extra field halved (the two runs were minutes apart, so take that as a lead, not a proof); its average response to debt stayed about the same.

What this does not show: that Jev is a good credit model (it was not trained for that), how any lender would behave, or anything about ZIPs outside these three. All applicants are synthetic.

I wrote the plan down before running the main test, kept every raw response, and the whole run cost under a dollar. Code and data: [repo link]

#AI #ResponsibleAI #BuildInPublic
