<TaskTemplate>
  <Header>
    <Title>TASK: {{TITLE}}</Title>
    <Overview>
      <Purpose>
        <Label>Purpose:</Label>
        <Text>Plan → execute → track all edits with diffs and notes so other models can audit easily.</Text>
      </Purpose>
      <Usage>
        <Label>How to use:</Label>
        <Text>One AI agent fills all placeholders, executes each phase in order, updates “Execution” blocks and diffs, then hands off to another AI agent for review in each phase’s Review block.</Text>
      </Usage>
    </Overview>
  </Header>
  <Section id="meta">
    <Heading>0) META</Heading>
    <MetaTemplate>
      <TaskId>{{T#}}</TaskId>
      <Title>{{TITLE}}</Title>
      <RepoRoot>{{./ or path}}</RepoRoot>
      <Branch>{{feature/slug}}</Branch>
      <Status>planning|in-progress|blocked|done</Status>
      <Goal>{{one-sentence measurable outcome}}</Goal>
      <NonGoals>
        <Item>{{optional}}</Item>
      </NonGoals>
      <Dependencies>
        <Item>{{PR/issue/ref}}</Item>
      </Dependencies>
      <Constraints>
        <Item>{{perf|security|compat|style|api-stability}}</Item>
      </Constraints>
      <AcceptanceCriteria>
        <Criterion>{{AC1: clear, testable}}</Criterion>
        <Criterion>{{AC2}}</Criterion>
      </AcceptanceCriteria>
      <TestStrategy>unit|integration|e2e (brief)</TestStrategy>
      <Rollback>how to revert cleanly</Rollback>
      <Owner>@{{handle}}</Owner>
    </MetaTemplate>
  </Section>
  <Section id="context">
    <Heading>1) CONTEXT (brief)</Heading>
    <List type="bullet">
      <Item>
        <Label>Current behavior:</Label>
        <Text>{{what exists now}}</Text>
      </Item>
      <Item>
        <Label>Target behavior:</Label>
        <Text>{{what will exist after completion}}</Text>
      </Item>
      <Item>
        <Label>Interfaces touched (APIs/CLIs/UX):</Label>
        <Text>{{list}}</Text>
      </Item>
      <Item>
        <Label>Risk notes:</Label>
        <Text>{{edge cases, data migrations, security concerns}}</Text>
      </Item>
    </List>
  </Section>
  <Section id="high_level_plan">
    <Heading>2) HIGH-LEVEL PLAN</Heading>
    <Instruction>List the phases AI will execute. Keep each phase atomic and verifiable.</Instruction>
    <PhasesTemplate>
      <Phase>
        <Id>P1</Id>
        <Name>{{short name}}</Name>
        <Summary>{{what changes}}</Summary>
      </Phase>
      <Phase>
        <Id>P2</Id>
        <Name>{{short name}}</Name>
        <Summary>{{what changes}}</Summary>
      </Phase>
    </PhasesTemplate>
  </Section>
  <Section id="phases">
    <Heading>3) PHASES</Heading>
    <Callout>Duplicate the Phase Block below for each phase (P1, P2, …). Fill Plan first, then after execution fill Execution + Diffs + Results. Use Review.</Callout>
    <PhaseTemplate>
      <PhaseHeading>Phase {{P#}} — {{NAME}}</PhaseHeading>
      <Subsection id="3.1">
        <Title>3.1 Plan (to be written <Emphasis>before</Emphasis> editing)</Title>
        <PhasePlanTemplate>
          <PhaseId>{{P#}}</PhaseId>
          <Intent>{{what this phase achieves}}</Intent>
          <Edits>
            <Edit>
              <Path>{{relative/file.ext}}</Path>
              <Operation>add|modify|move|delete</Operation>
              <Rationale>{{why}}</Rationale>
              <Method>{{how: algorithm/steps}}</Method>
            </Edit>
          </Edits>
          <Commands>
            <Command>bash&gt; {{cmd to run}}</Command>
            <Command>bash&gt; {{tests/lint/build}}</Command>
          </Commands>
          <TestsExpected>
            <Test>
              <Name>{{test or manual check}}</Name>
              <Expectation>{{pass condition}}</Expectation>
            </Test>
          </TestsExpected>
          <Links>
            <Link>{{spec|issue|doc}}</Link>
          </Links>
          <ExitCriteria>
            <Criterion>{{what must be true to call this phase done}}</Criterion>
          </ExitCriteria>
        </PhasePlanTemplate>
      </Subsection>
      <Subsection id="3.2">
        <Title>3.2 Execution (filled <Emphasis>after</Emphasis> editing)</Title>
        <List type="bullet">
          <Item>
            <Label>Status:</Label>
            <Text>done|blocked|needs-followup</Text>
          </Item>
          <Item>
            <Label>Files changed (summary):</Label>
            <NestedList type="bullet">
              <Item>`{{path}}` — {{add/modify/delete}} (reason: {{short}})</Item>
            </NestedList>
          </Item>
          <Item>
            <Label>Notes:</Label>
            <Text>{{decisions, deviations from plan}}</Text>
          </Item>
        </List>
      </Subsection>
      <Subsection id="3.3">
        <Title>3.3 Diffs (one unified patch block per file)</Title>
        <CodeBlock language="diff"><![CDATA[
# {{relative/file.ext}}
@@ {{hunk header}} @@
- {{old line}}
+ {{new line}}
]]></CodeBlock>
        <Callout>If large, add multiple blocks:</Callout>
        <CodeBlock language="diff"><![CDATA[
# {{another/file.ext}}
@@ ...
- ...
+ ...
]]></CodeBlock>
      </Subsection>
      <Subsection id="3.4">
        <Title>3.4 Inline Comments Added in Code (if any)</Title>
        <InlineCommentsTemplate>
          <Comment>
            <Path>{{file}}</Path>
            <Line>{{n}}</Line>
            <Explanation>{{why this is safe/correct}}</Explanation>
          </Comment>
        </InlineCommentsTemplate>
      </Subsection>
      <Subsection id="3.5">
        <Title>3.5 Results</Title>
        <ResultsTemplate>
          <Build>passed|failed</Build>
          <Lint>passed|failed</Lint>
          <Tests>
            <Test>
              <Name>{{unit xyz}}</Name>
              <Result>pass|fail</Result>
            </Test>
            <Test>
              <Name>{{manual: click-through}}</Name>
              <Result>pass|fail</Result>
            </Test>
          </Tests>
          <Artifacts>
            <Item>{{binary/log/report path if any}}</Item>
          </Artifacts>
          <MeetsExitCriteria>true</MeetsExitCriteria>
        </ResultsTemplate>
      </Subsection>
      <Subsection id="3.6">
        <Title>3.6 Review</Title>
        <ReviewTemplate>
          <Reviewer>claude</Reviewer>
          <Checklist>
            <Item name="correctness">ok|concern</Item>
            <Item name="safety/security">ok|concern</Item>
            <Item name="style/consistency">ok|concern</Item>
            <Item name="test_coverage">ok|concern</Item>
            <Item name="perf/regression">ok|concern</Item>
          </Checklist>
          <Findings>
            <Item>{{observations}}</Item>
          </Findings>
          <Suggestions>
            <Item>{{polish ideas / refactors}}</Item>
          </Suggestions>
          <Verdict>approve|request-changes</Verdict>
        </ReviewTemplate>
      </Subsection>
    </PhaseTemplate>
  </Section>
  <Section id="traceability">
    <Heading>4) CROSS-PHASE TRACEABILITY</Heading>
    <Instruction>Link ACs → phases → files to prove coverage.</Instruction>
    <TraceabilityTemplate>
      <Trace>
        <AcceptanceCriterion>{{AC1}}</AcceptanceCriterion>
        <Phases>
          <Phase>P1</Phase>
          <Phase>P3</Phase>
        </Phases>
        <Files>
          <File>{{src/a.ts}}</File>
          <File>{{tests/a.test.ts}}</File>
        </Files>
        <Verification>{{how we assert AC1}}</Verification>
      </Trace>
    </TraceabilityTemplate>
  </Section>
  <Section id="post_task_summary">
    <Heading>5) POST-TASK SUMMARY (fill at the end)</Heading>
    <PostTaskSummaryTemplate>
      <TaskStatus>done|partial|abandoned</TaskStatus>
      <MergedTo>{{branch or tag}}</MergedTo>
      <Delta>
        <FilesAdded>{{n}}</FilesAdded>
        <FilesModified>{{n}}</FilesModified>
        <FilesDeleted>{{n}}</FilesDeleted>
        <LocAdded>{{n}}</LocAdded>
        <LocRemoved>{{n}}</LocRemoved>
      </Delta>
      <KeyDiffRefs>
        <Reference>
          <Path>{{file}}</Path>
          <Gist>{{1-line what changed}}</Gist>
        </Reference>
      </KeyDiffRefs>
      <RemainingRisks>
        <Item>{{if any}}</Item>
      </RemainingRisks>
      <Followups>
        <Item>{{T# or issue links}}</Item>
      </Followups>
    </PostTaskSummaryTemplate>
  </Section>
  <Section id="checklist">
    <Heading>6) QUICK CHECKLIST (tick as you go)</Heading>
    <Checklist>
      <Item status="pending">Phases defined with clear exit criteria</Item>
      <Item status="pending">Each change has rationale and test</Item>
      <Item status="pending">Diffs captured and readable</Item>
      <Item status="pending">Lint/build/tests green</Item>
      <Item status="pending">Acceptance criteria satisfied</Item>
      <Item status="pending">Review completed (per phase)</Item>
      <Item status="pending">Rollback path documented</Item>
    </Checklist>
  </Section>
  <Section id="pr_message">
    <Heading>Optional: Minimal PR Message (can be pasted)</Heading>
    <CodeBlock language="markdown"><![CDATA[
Title: {{T#}} {{TITLE}}

Why:
- {{problem}}

What:
- {{key changes (bulleted, 1 line each)}}

Tests:
- {{how verified}}

Risks/Mitigations:
- {{brief}}
]]></CodeBlock>
  </Section>
</TaskTemplate>
