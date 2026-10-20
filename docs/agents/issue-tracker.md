# Issue tracker: GitHub

本仓库的 issues 和 specs 均统一维护在 GitHub issues 中。所有操作一律使用 `gh` CLI。

## 常用约定

- **创建 issue**：`gh issue create --title "..." --body "..."`。多行正文请使用 heredoc 语法。
- **读取 issue**：`gh issue view <number> --json number,title,body,labels,comments`。
- **列出 issues**：`gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'`，按需配合 `--label` 与 `--state` 过滤。
- **将 issue 设为父 issue 的 sub-issue**：`gh issue create --parent <parent> ...`，或后续使用 `gh issue edit <parent> --add-sub-issue <child>`（适用于 `gh` 2.94+）。较旧版本 `gh`：`gh api --method POST repos/<owner>/<repo>/issues/<parent>/sub_issues -F sub_issue_id=<child-db-id>`（database id，详见下文 **Blocking** 说明）。若不支持 sub-issues，在子 issue 正文顶部标注 `Part of #<parent>`。
- **在 issue 下发表评论**：`gh issue comment <number> --body "..."`
- **添加 / 移除 label**：`gh issue edit <number> --add-label "..."` / `--remove-label "..."`
- **关闭 issue**：`gh issue close <number> --comment "..."`

从 `git remote -v` 推断所属仓库；在 Git 克隆目录内运行时 `gh` 会自动完成推断。

## 将 Pull Requests 作为分诊对象

**将 PR 作为需求来源：否（no）。** _（若本仓库将外部 PR 视为功能请求，可修改为 `yes`；`/triage` skill 会读取该标记。）_

当设置为 `yes` 时，PR 将走与 issues 相同的 labels 与状态流，使用对应的 `gh pr` 命令：

- **读取 PR**：`gh pr view <number> --comments`，以及使用 `gh pr diff <number>` 查看 diff。
- **列出待分诊的外部 PR**：`gh api --paginate 'repos/{owner}/{repo}/pulls?state=open' --jq '.[] | select(.author_association | IN("OWNER","MEMBER","COLLABORATOR") | not) | {number, title, author: .user.login, author_association, labels: [.labels[].name]}'`.
- **评论 / 标记 label / 关闭**：`gh pr comment`、`gh pr edit --add-label`/`--remove-label`、`gh pr close`。

GitHub 在 issues 和 PRs 之间共享同一数字编号空间，因此单独的 `#42` 可能指代二者之一：可先使用 `gh pr view 42` 尝试解析，若失败则回退至 `gh issue view 42`。

## 当某个 skill 说明“发布至 issue tracker”时

创建一个 GitHub issue。

## 当某个 skill 说明“获取相关 ticket”时

按照上述 **读取 issue** 的方式进行读取。

## Wayfinding 路径操作

由 `/wayfinder` 使用。**map** 是一个单独的 issue，**child** issues 作为具体的子任务 tickets。

- **Map**：带有 `wayfinder:map` 标签的单个 issue，正文中包含 Notes（笔记）/ Decisions-so-far（既定决策）/ Fog（未明雾区）。创建命令：`gh issue create --label wayfinder:map`。
- **Child ticket**：作为 GitHub sub-issue 关联至 map 的 issue（详见上文 **将 issue 设为父 issue 的 sub-issue**）。在未启用 sub-issues 的环境中，将 child 添加到 map 正文的任务列表（task list）中，并在 child 正文顶部添加 `Part of #<map>`。Labels 格式：`wayfinder:<type>`（可选 `research`/`prototype`/`grilling`/`task`）。一旦被认领，ticket 会分配给当前负责的开发者。
- **Blocking 依赖阻塞**：GitHub 原生的 **issue dependencies**，也是 UI 上直观展示的标准形式。通过以下命令添加阻塞依赖边：`gh api --method POST repos/<owner>/<repo>/issues/<child>/dependencies/blocked_by -F issue_id=<blocker-db-id>`，其中 `<blocker-db-id>` 为 blocker 的数字型 **database id**（通过 `gh api repos/<owner>/<repo>/issues/<n> --jq .id` 获取，**注意不是** `#number` 或 `node_id`）。GitHub 会在 `issue_dependencies_summary.blocked_by` 中汇报（仅包含未关闭的 blocker，即当前活跃门禁）。若原生依赖不可用，可在 child 正文顶部回退标注 `Blocked by: #<n>, #<n>`。当所有 blocker 关闭后，ticket 自动解除阻塞。
- **Frontier 查询（寻路前沿）**：列出 map 的打开状态 children（`gh issue list --state open`，范围限定在 map 的 sub-issues / task list），排除存在未解除 blocker（`issue_dependencies_summary.blocked_by > 0`，或 `Blocked by` 行中存在 open issue）或已有被分配者（assignee）的项；按 map 中排列顺序取第一个有效项。
- **认领（Claim）**：`gh issue edit <n> --add-assignee @me`，作为当前 session 的首个写操作。
- **解决（Resolve）**：`gh issue comment <n> --body "<answer>"`，然后执行 `gh issue close <n>`，最后将上下文指针（概要 + 链接）追加至 map 的 Decisions-so-far 区块中。
