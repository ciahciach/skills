## What it does

`prototype` writes **throwaway code that answers a question**: does this state model feel right, or what should this screen look like. The question comes first and decides what you build. A prototype that answers the wrong question is wasted, however good it looks.

Throwaway is a constraint on how the code is *written*, not a promise to destroy it. No tests, no error handling beyond what makes it run, no abstractions, no persistence, because none of that helps you learn the one thing you're trying to learn. The answer goes into the real code, and the handoff says where the prototype can be found.

## When to reach for it

Type `/prototype`, or the [agent](https://www.aihero.dev/ai-coding-dictionary/agent) reaches for it automatically when a task fits.

Reach for it the moment you hit a question you can't settle by talking: a state machine whose edge cases you can't hold in your head, a screen you can't picture until you see three versions side by side. [Grilling](https://www.aihero.dev/ai-coding-dictionary/grilling) sessions grow long on these questions. The agent rephrases, you guess, and the scope grows. Stop grilling, build the throwaway version, look at it, then answer in one line. If instead something already built is misbehaving and you want to know why, use [diagnosing-bugs](https://aihero.dev/skills-diagnosing-bugs); prototyping explores what to build, not why the built thing is broken.

You will also arrive here without choosing to. [wayfinder](https://aihero.dev/skills-wayfinder) files `prototype` decision [tickets](https://www.aihero.dev/ai-coding-dictionary/ticket) on its map, and you work one with this skill.

## Two branches

The question picks the branch, and the branches produce different artifacts:

- **"Does this logic / state model feel right?"**: a **single shareable HTML file**. One self-contained page, no build and no server, that someone opens by double-clicking. It carries a labelled state panel that re-renders after every click, free-play buttons for poking at the model in any order, and tabbed **guided walkthroughs** (one scenario per tab, each with the ordered buttons to press underneath it). Everything is labelled in domain language, so you can hand it to a designer, a PM or a domain expert and let them try the model themselves. The logic behind the page is a small pure module (a reducer, a machine, a set of functions) with no DOM code in it, so you can move the validated version straight into the real code.
- **"What should this look like?"**: several **radically different** UI variations on one route, switchable from a floating bottom bar and a `?variant=` URL param. Variants must disagree about structure, not colour; three card grids with small tweaks answer nothing. They render inside a real page wherever possible, against real data and real density, because a variant judged on an empty page always looks fine.

Both keep state in memory, start with no setup, and show you the full state after every step. The moment you find yourself hardening one (adding a test, wiring the real database, generalising for a case you might want later), you have stopped prototyping.

## The prototype is a primary source

A finished prototype leaves two things, and they go to different places.

You record the **answer** (the verdict plus the question it settled) somewhere permanent: a commit message, an ADR, the implementation issue. Main keeps the answer, in the real code.

The **prototype** is the runnable evidence the answer came from. It doesn't belong in main, because nobody maintains it and it goes stale fast. The [context pointer](https://www.aihero.dev/ai-coding-dictionary/context-pointer) tells the next agent whether it can open the artifact from another checkout:

- **Linked (illustrative URLs):** Artifact: `https://example.com/prototypes/revisions/42/layout-b.html`. Human acceptance: `https://example.com/reviews/17#verdict` records the choice of layout B. Verification: `https://example.com/checks/61` records passing Edge keyboard and validation checks for revision 42. Compilation and backend qualification are not applicable. The next agent uses the revision link rather than looking for the original checkout; neither evidence link stands in for the artifact.
- **Local only:** The Excel comparison [browser checkpoint](https://github.com/ciahciach/skills/issues/8#issuecomment-7110560043) reports passing checks but doesn't host the HTML. Its last known location was `skills/engineering/setup-matt-pocock-skills/excel-workflow.prototype.html` in the original [`research-html-userform-prototyping-tool` worktree](https://github.com/ciahciach/skills/issues/8#issuecomment-7110324145); current retrieval is unverified. The separate [human acceptance](https://github.com/ciahciach/skills/issues/8#issuecomment-7110586570) covers only the browser stage. At that checkpoint, native execution and VBA compilation were not verified. The [runtime checkpoint](https://github.com/ciahciach/skills/issues/8#issuecomment-7110022851) records missing backend qualification.

A handoff does not authorize committing, pushing or publishing a local artifact.

## Common questions

**Wait, isn't the prototype supposed to be deleted?**
Not by default. A prose summary of a prototype loses the thing that made it convincing. The skill treats the prototype as a [primary source](https://www.aihero.dev/ai-coding-dictionary/primary-source) for the next [session](https://www.aihero.dev/ai-coding-dictionary/session). If you separately authorize preserving it in Git, it goes on a throwaway branch out of main, not into the production code.

**It used to build a terminal app. Where did that go?**
The logic branch now emits a single shareable HTML file instead. A terminal app can only be driven by someone with the repo cloned and a runtime installed, which rules out the people whose opinion the prototype needs: the designer, the PM, the domain expert who knows what the state model is supposed to mean. One self-contained file that opens by double-click and still works after being emailed can be driven by anyone. The pure logic module underneath is unchanged, and is still the part you move into the real code.

**An agent told me to `/prototype` when I should have been implementing.**
This is a known naming problem. An agent that does not know the flow reads `prototype`, a generic and appealing word, as "the obvious next step" once tickets exist. So agents recommend it by name even where the design was settled in conversation. If you already know what to build, the next step is `/implement`, per ticket. Reach for a prototype only when a specific design question is unresolved and talking won't resolve it.

**Should I prototype the whole application before building any of its production features (say, to demo it to prospects)?**
That is a different artifact that happens to share this skill's name. A prototype here is scoped to one question, and "what is the whole app?" isn't one. A full-app prototype has no natural stopping point, so it drifts into being the production app: the cleanup pass never happens, and code written under prototype rules (no tests, no error handling) ends up in front of users. If you need a sales demo, build it as a demo on purpose and be explicit that none of it is production. If you need to settle a design question, cut it down to that question.

**How do I run it in its own session?**
A prototype lives in its own directory and generates a lot of [context](https://www.aihero.dev/ai-coding-dictionary/context) you don't want in the thread that asked the question, so run it somewhere else. Use [handoff](https://aihero.dev/skills-handoff) to move the work into that session and bring back the answer and evidence without the full conversation.

**Isn't this the fastest possible way to burn tokens?**
It can be, if you prototype questions you could have answered by talking, or let one prototype sprawl across a whole feature. The comparison that matters isn't tokens against zero; it's [tokens](https://www.aihero.dev/ai-coding-dictionary/token) against building the wrong state model and finding out after it has production callers. Keep the question narrow and the run short, and the spend stays proportionate.

## It's working if

- You can say in one sentence what question the prototype exists to answer, and it's written at the top of the demo, not just in your head.
- Someone who doesn't read code can drive the logic demo. They open the file, press the buttons in a walkthrough tab, and describe what they see in their own words.
- Someone says "wait, that shouldn't be possible" or "huh, I assumed X". That's a bug in the *idea*, which is what the prototype is for.
- The UI variants disagree about layout and information hierarchy, not just colour and copy, and the feedback you get is "the header from B with the sidebar from C".
- It is answered in one sitting. If you're still building it a day later, the question was too big; split it.
- The next agent can tell where to retrieve the reviewed prototype, or exactly which local worktree or machine it needs. It can also tell what the human accepted and what was actually verified.

## Where it fits

`prototype` is a **reach-for-it-anytime standalone**: you use it to settle one design question, then go back to your work. Another skill also runs it.

The skill that runs it most is [wayfinder](https://aihero.dev/skills-wayfinder). A wayfinder map is made of **decision tickets**, and `prototype` is one of the four types a ticket can be: the one used when the blocking question is "how should this look" or "how should it behave", which no amount of discussion resolves. When a discussion is vague, wayfinder makes something concrete to react to, and this skill builds that thing. The answer resolves a prototype ticket, and the ticket records the artifact's availability.

The other neighbours are upstream and downstream of that. [grill-me](https://aihero.dev/skills-grill-me) and [grill-with-docs](https://aihero.dev/skills-grill-with-docs) answer grillable questions; the ungrillable ones come here instead, and the one-line answer goes back into the interview. Downstream, a validated state model or UI direction becomes settled input for [to-spec](https://aihero.dev/skills-to-spec), which can inline the decision-rich snippet the prototype produced rather than describing it in prose. For anything else, [ask-matt](https://aihero.dev/skills-ask-matt) routes you over the whole set.
