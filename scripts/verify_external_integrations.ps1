[CmdletBinding()]
param(
    [switch]$Help,
    [switch]$DryRun,
    [switch]$EnableSmoke,
    [switch]$FailOnSmokeError,
    [switch]$EnableBusinessClosure,
    [string]$Targets = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Usage {
    Write-Host "Usage: .\scripts\verify_external_integrations.ps1 [-DryRun] [-EnableSmoke] [-FailOnSmokeError] [-EnableBusinessClosure] [-Targets <names>]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Help      Show this help message."
    Write-Host "  -DryRun    Only check configuration, never call external APIs."
    Write-Host "  -EnableSmoke  Run minimal API smoke checks after config READY."
    Write-Host "  -FailOnSmokeError  Return non-zero when any enabled smoke check fails."
    Write-Host "  -EnableBusinessClosure  Create reversible Jira/Zentao/Jenkins business probes."
    Write-Host "  -Targets   Optional comma-separated target names: DingTalk, GitHub Actions, Jenkins, Jira, Zentao."
    Write-Host ""
    Write-Host "Environment variables:"
    Write-Host "  DINGTALK_WEBHOOK_URL, optional DINGTALK_WEBHOOK_SECRET"
    Write-Host "  WEITESTING_GITHUB_TOKEN or GITHUB_TOKEN"
    Write-Host "  WEITESTING_GITHUB_REPOSITORY or GITHUB_REPOSITORY"
    Write-Host "  WEITESTING_GITHUB_WORKFLOW_FILE or GITHUB_WORKFLOW_FILE"
    Write-Host "  JENKINS_BASE_URL, JENKINS_JOB_NAME, JENKINS_USERNAME, JENKINS_API_TOKEN"
    Write-Host "  JIRA_BASE_URL, JIRA_PROJECT_KEY, JIRA_EMAIL, JIRA_TOKEN"
    Write-Host "  ZENTAO_BASE_URL, ZENTAO_PRODUCT, ZENTAO_TOKEN or ZENTAO_ACCOUNT + ZENTAO_PASSWORD"
    Write-Host "  Optional business closure: WEITESTING_BUSINESS_CLOSURE_PREFIX, JIRA_ISSUE_TYPE, ZENTAO_MODULE"
}

function Get-MaskedValue {
    param([string]$Value)

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return "<EMPTY>"
    }
    if ($Value.Length -le 8) {
        return "****"
    }
    return ("{0}****{1}" -f $Value.Substring(0, 4), $Value.Substring($Value.Length - 2, 2))
}

function Get-RedactedMessage {
    param([string]$Message)

    $redacted = [string]$Message
    $secretEnvNames = @(
        "DINGTALK_WEBHOOK_URL",
        "DINGTALK_WEBHOOK_SECRET",
        "GITHUB_TOKEN",
        "WEITESTING_GITHUB_TOKEN",
        "JENKINS_API_TOKEN",
        "JIRA_TOKEN",
        "ZENTAO_TOKEN",
        "ZENTAO_PASSWORD"
    )
    foreach ($envName in $secretEnvNames) {
        $secretValue = [Environment]::GetEnvironmentVariable($envName)
        if (-not [string]::IsNullOrWhiteSpace($secretValue)) {
            $redacted = $redacted.Replace($secretValue, "***REDACTED***")
        }
    }
    $redacted = [regex]::Replace(
        $redacted,
        "(?i)(access_token|token|secret|password|api[_-]?key|authorization)=([^&\s]+)",
        '$1=***REDACTED***'
    )
    return $redacted
}

function Get-ExternalErrorMessage {
    param([object]$ErrorRecord)

    $message = [string]$ErrorRecord.Exception.Message
    $response = $ErrorRecord.Exception.Response
    if ($null -ne $response) {
        try {
            $body = $null
            if ($null -ne $response.Content) {
                $body = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
            }
            elseif ($response.PSObject.Methods["GetResponseStream"]) {
                $stream = $response.GetResponseStream()
                if ($null -ne $stream) {
                    $reader = [System.IO.StreamReader]::new($stream)
                    try {
                        $body = $reader.ReadToEnd()
                    }
                    finally {
                        $reader.Dispose()
                    }
                }
            }
            if (-not [string]::IsNullOrWhiteSpace($body)) {
                $message = "$message Body: $body"
            }
        }
        catch {}
    }
    return Get-RedactedMessage -Message $message
}

function Add-BusinessClosureFailure {
    param(
        [System.Collections.Generic.List[string]]$Failures,
        [string]$Name,
        [string]$Message
    )

    if (-not $Failures.Contains($Name)) {
        $Failures.Add($Name) | Out-Null
    }
    Write-Warning ("[BUSINESS] {0} cleanup failed: {1}" -f $Name, (Get-RedactedMessage -Message $Message))
}

function Get-ZentaoToken {
    param([string]$BaseUrl)

    $account = [Environment]::GetEnvironmentVariable("ZENTAO_ACCOUNT")
    $password = [Environment]::GetEnvironmentVariable("ZENTAO_PASSWORD")
    if (-not [string]::IsNullOrWhiteSpace($account) -and -not [string]::IsNullOrWhiteSpace($password)) {
        $payload = @{
            account = $account
            password = $password
        } | ConvertTo-Json -Depth 4
        $response = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api.php/v1/tokens" -ContentType "application/json" -Body $payload -TimeoutSec 10
        if ([string]::IsNullOrWhiteSpace([string]$response.token)) {
            throw "Zentao token endpoint returned an empty token."
        }

        return [string]$response.token
    }

    $token = [Environment]::GetEnvironmentVariable("ZENTAO_TOKEN")
    if (-not [string]::IsNullOrWhiteSpace($token)) {
        return $token
    }

    throw "Zentao token is missing and ZENTAO_ACCOUNT/ZENTAO_PASSWORD are incomplete."
}

function Get-EnvValue {
    param([string[]]$Names)

    foreach ($name in $Names) {
        if ($name.Contains("+")) {
            $parts = @($name -split "\+" | ForEach-Object { $_.Trim() } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
            $allPresent = $true
            foreach ($part in $parts) {
                $partValue = [Environment]::GetEnvironmentVariable($part)
                if ([string]::IsNullOrWhiteSpace($partValue)) {
                    $allPresent = $false
                    break
                }
            }
            if ($allPresent) {
                return "<COMPOSITE>"
            }
            continue
        }

        $value = [Environment]::GetEnvironmentVariable($name)
        if (-not [string]::IsNullOrWhiteSpace($value)) {
            return $value
        }
    }

    return $null
}

function Get-DingTalkSignedWebhookUrl {
    param(
        [string]$WebhookUrl,
        [string]$Secret
    )

    if ([string]::IsNullOrWhiteSpace($WebhookUrl) -or [string]::IsNullOrWhiteSpace($Secret)) {
        return $WebhookUrl
    }

    $timestamp = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
    $stringToSign = "$timestamp`n$Secret"
    $secretBytes = [System.Text.Encoding]::UTF8.GetBytes($Secret)
    $signBytes = [System.Text.Encoding]::UTF8.GetBytes($stringToSign)
    $hmac = [System.Security.Cryptography.HMACSHA256]::new($secretBytes)
    try {
        $signature = [Convert]::ToBase64String($hmac.ComputeHash($signBytes))
    }
    finally {
        $hmac.Dispose()
    }
    $encodedSignature = [System.Net.WebUtility]::UrlEncode($signature)
    $separator = if ($WebhookUrl.Contains("?")) { "&" } else { "?" }
    return "$WebhookUrl${separator}timestamp=$timestamp&sign=$encodedSignature"
}

function Get-IntegrationStatus {
    param(
        [string]$Name,
        [object[]]$RequiredEnvGroups
    )

    $missing = @()
    $requiredLabels = @()
    foreach ($envGroup in $RequiredEnvGroups) {
        $names = @($envGroup)
        $requiredLabels += ($names -join " or ")
        $value = Get-EnvValue -Names $names
        if ([string]::IsNullOrWhiteSpace($value)) {
            $missing += ($names -join " or ")
        }
    }

    return [PSCustomObject]@{
        Name = $Name
        Required = $requiredLabels
        Missing = $missing
        Ready = ($missing.Count -eq 0)
    }
}

function Invoke-SmokeChecks {
    param([System.Collections.Generic.List[object]]$Statuses)

    $failures = New-Object System.Collections.Generic.List[string]
    foreach ($status in $Statuses) {
        if (-not $status.Ready) {
            continue
        }
        switch ($status.Name) {
            "DingTalk" {
                try {
                    $webhook = [Environment]::GetEnvironmentVariable("DINGTALK_WEBHOOK_URL")
                    $secret = [Environment]::GetEnvironmentVariable("DINGTALK_WEBHOOK_SECRET")
                    $signedWebhook = Get-DingTalkSignedWebhookUrl -WebhookUrl $webhook -Secret $secret
                    $payload = @{
                        msgtype = "text"
                        text = @{
                            content = "WeiTesting external integration smoke"
                        }
                    } | ConvertTo-Json -Depth 4
                    Invoke-RestMethod -Method Post -Uri $signedWebhook -ContentType "application/json; charset=utf-8" -Body $payload -TimeoutSec 8 | Out-Null
                    Write-Host "[SMOKE] DingTalk webhook accepted message."
                }
                catch {
                    $failures.Add($status.Name) | Out-Null
                    Write-Warning ("[SMOKE] DingTalk failed: {0}" -f (Get-RedactedMessage -Message $_.Exception.Message))
                }
            }
            "GitHub Actions" {
                try {
                    $repo = Get-EnvValue -Names @("WEITESTING_GITHUB_REPOSITORY", "GITHUB_REPOSITORY")
                    $workflow = Get-EnvValue -Names @("WEITESTING_GITHUB_WORKFLOW_FILE", "GITHUB_WORKFLOW_FILE")
                    $token = Get-EnvValue -Names @("WEITESTING_GITHUB_TOKEN", "GITHUB_TOKEN")
                    $headers = @{
                        Authorization = "Bearer $token"
                        Accept = "application/vnd.github+json"
                        "X-GitHub-Api-Version" = "2022-11-28"
                    }
                    $uri = "https://api.github.com/repos/$repo/actions/workflows/$workflow"
                    Invoke-RestMethod -Method Get -Uri $uri -Headers $headers -TimeoutSec 10 | Out-Null
                    Write-Host "[SMOKE] GitHub workflow metadata reachable."
                }
                catch {
                    $failures.Add($status.Name) | Out-Null
                    Write-Warning ("[SMOKE] GitHub Actions failed: {0}" -f (Get-RedactedMessage -Message $_.Exception.Message))
                }
            }
            "Jenkins" {
                try {
                    $base = [Environment]::GetEnvironmentVariable("JENKINS_BASE_URL").TrimEnd("/")
                    $job = [Environment]::GetEnvironmentVariable("JENKINS_JOB_NAME")
                    $username = [Environment]::GetEnvironmentVariable("JENKINS_USERNAME")
                    $token = [Environment]::GetEnvironmentVariable("JENKINS_API_TOKEN")
                    $pair = "{0}:{1}" -f $username, $token
                    $bytes = [System.Text.Encoding]::UTF8.GetBytes($pair)
                    $basic = [System.Convert]::ToBase64String($bytes)
                    $headers = @{ Authorization = "Basic $basic" }
                    $uri = "$base/job/$job/api/json"
                    Invoke-RestMethod -Method Get -Uri $uri -Headers $headers -TimeoutSec 10 | Out-Null
                    Write-Host "[SMOKE] Jenkins job metadata reachable."
                }
                catch {
                    $failures.Add($status.Name) | Out-Null
                    Write-Warning ("[SMOKE] Jenkins failed: {0}" -f (Get-RedactedMessage -Message $_.Exception.Message))
                }
            }
            "Jira" {
                try {
                    $base = [Environment]::GetEnvironmentVariable("JIRA_BASE_URL").TrimEnd("/")
                    $projectKey = [Environment]::GetEnvironmentVariable("JIRA_PROJECT_KEY")
                    $email = [Environment]::GetEnvironmentVariable("JIRA_EMAIL")
                    $token = [Environment]::GetEnvironmentVariable("JIRA_TOKEN")
                    $pair = "{0}:{1}" -f $email, $token
                    $bytes = [System.Text.Encoding]::UTF8.GetBytes($pair)
                    $basic = [System.Convert]::ToBase64String($bytes)
                    $headers = @{ Authorization = "Basic $basic" }
                    $accountUri = "$base/rest/api/3/myself"
                    Invoke-RestMethod -Method Get -Uri $accountUri -Headers $headers -TimeoutSec 10 | Out-Null
                    Write-Host "[SMOKE] Jira account API reachable."
                    $encodedProjectKey = [System.Uri]::EscapeDataString($projectKey)
                    $projectUri = "$base/rest/api/3/project/$encodedProjectKey"
                    Invoke-RestMethod -Method Get -Uri $projectUri -Headers $headers -TimeoutSec 10 | Out-Null
                    Write-Host ("[SMOKE] Jira project {0} reachable." -f $projectKey)
                }
                catch {
                    $failures.Add($status.Name) | Out-Null
                    Write-Warning ("[SMOKE] Jira failed: {0}" -f (Get-RedactedMessage -Message $_.Exception.Message))
                }
            }
            "Zentao" {
                try {
                    $base = [Environment]::GetEnvironmentVariable("ZENTAO_BASE_URL").TrimEnd("/")
                    $token = Get-ZentaoToken -BaseUrl $base
                    $product = [Environment]::GetEnvironmentVariable("ZENTAO_PRODUCT")
                    $maskedToken = Get-MaskedValue -Value $token
                    $uri = "$base/api.php/v1/products/$product"
                    Invoke-RestMethod -Method Get -Uri $uri -Headers @{ token = $token } -TimeoutSec 10 | Out-Null
                    Write-Host "[SMOKE] Zentao product API reachable. token=$maskedToken"
                }
                catch {
                    $failures.Add($status.Name) | Out-Null
                    Write-Warning ("[SMOKE] Zentao failed: {0}" -f (Get-RedactedMessage -Message $_.Exception.Message))
                }
            }
        }
    }

    return $failures
}

function Get-ObjectPropertyValue {
    param(
        [object]$Object,
        [string]$PropertyName
    )

    if ($null -eq $Object) {
        return $null
    }
    $property = $Object.PSObject.Properties[$PropertyName]
    if ($null -eq $property) {
        return $null
    }
    return $property.Value
}

function Get-JiraIssueTypeName {
    param(
        [string]$BaseUrl,
        [hashtable]$Headers,
        [string]$ProjectKey,
        [string]$PreferredIssueType
    )

    if (-not [string]::IsNullOrWhiteSpace($PreferredIssueType)) {
        return $PreferredIssueType
    }

    $encodedProjectKey = [System.Uri]::EscapeDataString($ProjectKey)
    try {
        $meta = Invoke-RestMethod -Method Get -Uri "$BaseUrl/rest/api/3/issue/createmeta?projectKeys=$encodedProjectKey&expand=projects.issuetypes" -Headers $Headers -TimeoutSec 10
        $project = @($meta.projects)[0]
        $issueTypes = @($project.issuetypes)
        foreach ($name in @("Task", "任务", "Bug", "故障", "Story", "故事")) {
            $matched = $issueTypes | Where-Object { $_.name -eq $name } | Select-Object -First 1
            if ($null -ne $matched) {
                return [string]$matched.name
            }
        }
        if ($issueTypes.Count -gt 0) {
            return [string]$issueTypes[0].name
        }
    }
    catch {}

    return "Task"
}

function Invoke-JenkinsBuild {
    param(
        [string]$BaseUrl,
        [string]$JobName,
        [hashtable]$Headers,
        [string]$Stamp
    )

    try {
        Invoke-WebRequest -Method Post -Uri "$BaseUrl/job/$JobName/buildWithParameters?WEITESTING_CLOSURE_ID=$stamp" -Headers $Headers -TimeoutSec 10 | Out-Null
        return
    }
    catch {
        $message = Get-ExternalErrorMessage -ErrorRecord $_
        if ($message -notmatch "400|Bad Request") {
            throw
        }
    }

    Invoke-WebRequest -Method Post -Uri "$BaseUrl/job/$JobName/build" -Headers $Headers -TimeoutSec 10 | Out-Null
}

function Get-ZentaoOpenedBuild {
    param(
        [string]$BaseUrl,
        [string]$Token,
        [int]$Product
    )

    try {
        Invoke-RestMethod -Method Get -Uri "$BaseUrl/api.php/v1/products/$product/branches" -Headers @{ token = $Token } -TimeoutSec 10 | Out-Null
    }
    catch {}

    $configuredBuild = [Environment]::GetEnvironmentVariable("ZENTAO_OPENED_BUILD")
    if (-not [string]::IsNullOrWhiteSpace($configuredBuild)) {
        return $configuredBuild
    }

    return "trunk"
}

function Invoke-BusinessClosureChecks {
    param([System.Collections.Generic.List[object]]$Statuses)

    $failures = New-Object System.Collections.Generic.List[string]
    $prefix = [Environment]::GetEnvironmentVariable("WEITESTING_BUSINESS_CLOSURE_PREFIX")
    if ([string]::IsNullOrWhiteSpace($prefix)) {
        $prefix = "WeiTesting CI closure"
    }
    $stamp = [DateTimeOffset]::UtcNow.ToString("yyyyMMdd-HHmmss")

    foreach ($status in $Statuses) {
        if (-not $status.Ready) {
            continue
        }
        switch ($status.Name) {
            "Jira" {
                try {
                    $base = [Environment]::GetEnvironmentVariable("JIRA_BASE_URL").TrimEnd("/")
                    $projectKey = [Environment]::GetEnvironmentVariable("JIRA_PROJECT_KEY")
                    $email = [Environment]::GetEnvironmentVariable("JIRA_EMAIL")
                    $token = [Environment]::GetEnvironmentVariable("JIRA_TOKEN")
                    $pair = "{0}:{1}" -f $email, $token
                    $basic = [System.Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($pair))
                    $headers = @{ Authorization = "Basic $basic"; Accept = "application/json" }
                    $issueType = Get-JiraIssueTypeName -BaseUrl $base -Headers $headers -ProjectKey $projectKey -PreferredIssueType ([Environment]::GetEnvironmentVariable("JIRA_ISSUE_TYPE"))
                    $body = @{
                        fields = @{
                            project = @{ key = $projectKey }
                            summary = "$prefix Jira $stamp"
                            description = @{
                                type = "doc"
                                version = 1
                                content = @(@{
                                    type = "paragraph"
                                    content = @(@{ type = "text"; text = "Created by WeiTesting external business closure smoke." })
                                })
                            }
                            issuetype = @{ name = $issueType }
                        }
                    } | ConvertTo-Json -Depth 12
                    $created = Invoke-RestMethod -Method Post -Uri "$base/rest/api/3/issue" -Headers $headers -ContentType "application/json" -Body $body -TimeoutSec 10
                    Write-Host ("[BUSINESS] Jira issue created: {0}" -f $created.key)
                    try {
                        Invoke-RestMethod -Method Delete -Uri "$base/rest/api/3/issue/$($created.key)" -Headers $headers -TimeoutSec 10 | Out-Null
                        Write-Host ("[BUSINESS] Jira issue deleted: {0}" -f $created.key)
                    }
                    catch {
                        Add-BusinessClosureFailure -Failures $failures -Name "Jira" -Message $_.Exception.Message
                    }
                }
                catch {
                    $failures.Add($status.Name) | Out-Null
                    Write-Warning ("[BUSINESS] Jira failed: {0}" -f (Get-ExternalErrorMessage -ErrorRecord $_))
                }
            }
            "Jenkins" {
                try {
                    $base = [Environment]::GetEnvironmentVariable("JENKINS_BASE_URL").TrimEnd("/")
                    $job = [Environment]::GetEnvironmentVariable("JENKINS_JOB_NAME")
                    $username = [Environment]::GetEnvironmentVariable("JENKINS_USERNAME")
                    $token = [Environment]::GetEnvironmentVariable("JENKINS_API_TOKEN")
                    $basic = [System.Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes(("{0}:{1}" -f $username, $token)))
                    $headers = @{ Authorization = "Basic $basic" }
                    $crumb = $null
                    try {
                        $crumbInfo = Invoke-RestMethod -Method Get -Uri "$base/crumbIssuer/api/json" -Headers $headers -TimeoutSec 10
                        $crumb = $crumbInfo.crumb
                        $headers[$crumbInfo.crumbRequestField] = $crumb
                    }
                    catch {}
                    Invoke-JenkinsBuild -BaseUrl $base -JobName $job -Headers $headers -Stamp $stamp
                    Write-Host "[BUSINESS] Jenkins build trigger accepted."
                }
                catch {
                    $failures.Add($status.Name) | Out-Null
                    Write-Warning ("[BUSINESS] Jenkins failed: {0}" -f (Get-ExternalErrorMessage -ErrorRecord $_))
                }
            }
            "Zentao" {
                try {
                    $base = [Environment]::GetEnvironmentVariable("ZENTAO_BASE_URL").TrimEnd("/")
                    $token = Get-ZentaoToken -BaseUrl $base
                    $product = [Environment]::GetEnvironmentVariable("ZENTAO_PRODUCT")
                    $module = [Environment]::GetEnvironmentVariable("ZENTAO_MODULE")
                    if ([string]::IsNullOrWhiteSpace($module)) { $module = "0" }
                    $openedBuild = Get-ZentaoOpenedBuild -BaseUrl $base -Token $token -Product ([int]$product)
                    $body = @{
                        product = [int]$product
                        module = [int]$module
                        title = "$prefix Zentao $stamp"
                        severity = 3
                        pri = 3
                        openedBuild = $openedBuild
                        type = "codeerror"
                        steps = "Created by WeiTesting external business closure smoke."
                    } | ConvertTo-Json -Depth 8
                    $created = Invoke-RestMethod -Method Post -Uri "$base/api.php/v1/bugs" -Headers @{ token = $token } -ContentType "application/json" -Body $body -TimeoutSec 10
                    $bugId = Get-ObjectPropertyValue -Object $created -PropertyName "id"
                    if ($null -eq $bugId) {
                        $bug = Get-ObjectPropertyValue -Object $created -PropertyName "bug"
                        $bugId = Get-ObjectPropertyValue -Object $bug -PropertyName "id"
                    }
                    if ($null -eq $bugId) {
                        $bugId = "<unknown>"
                    }
                    Write-Host ("[BUSINESS] Zentao bug created: {0}" -f $bugId)
                    if ($bugId -ne "<unknown>") {
                        try {
                            Invoke-RestMethod -Method Delete -Uri "$base/api.php/v1/bugs/$bugId" -Headers @{ token = $token } -TimeoutSec 10 | Out-Null
                            Write-Host ("[BUSINESS] Zentao bug deleted: {0}" -f $bugId)
                        }
                        catch {
                            Add-BusinessClosureFailure -Failures $failures -Name "Zentao" -Message $_.Exception.Message
                        }
                    }
                }
                catch {
                    $failures.Add($status.Name) | Out-Null
                    Write-Warning ("[BUSINESS] Zentao failed: {0}" -f (Get-ExternalErrorMessage -ErrorRecord $_))
                }
            }
        }
    }

    return $failures
}

function Get-TargetSet {
    param([string]$TargetNames)

    $targetSet = @{}
    if ([string]::IsNullOrWhiteSpace($TargetNames)) {
        return $targetSet
    }

    foreach ($target in ($TargetNames -split ",")) {
        $normalized = $target.Trim().ToLowerInvariant()
        if (-not [string]::IsNullOrWhiteSpace($normalized)) {
            $targetSet[$normalized] = $true
        }
    }

    return $targetSet
}

if ($Help) {
    Write-Usage
    exit 0
}

$definitions = @(
    @{ Name = "DingTalk"; Required = @("DINGTALK_WEBHOOK_URL") },
    @{ Name = "GitHub Actions"; Required = @(
        @("WEITESTING_GITHUB_TOKEN", "GITHUB_TOKEN"),
        @("WEITESTING_GITHUB_REPOSITORY", "GITHUB_REPOSITORY"),
        @("WEITESTING_GITHUB_WORKFLOW_FILE", "GITHUB_WORKFLOW_FILE")
    ) },
    @{ Name = "Jenkins"; Required = @("JENKINS_BASE_URL", "JENKINS_JOB_NAME", "JENKINS_USERNAME", "JENKINS_API_TOKEN") },
    @{ Name = "Jira"; Required = @("JIRA_BASE_URL", "JIRA_PROJECT_KEY", "JIRA_EMAIL", "JIRA_TOKEN") },
    @{ Name = "Zentao"; Required = @("ZENTAO_BASE_URL", "ZENTAO_PRODUCT", @("ZENTAO_TOKEN", "ZENTAO_ACCOUNT+ZENTAO_PASSWORD")) }
)

$targetSet = Get-TargetSet -TargetNames $Targets
if ($targetSet.Count -gt 0) {
    $definitions = @($definitions | Where-Object { $targetSet.ContainsKey($_.Name.ToLowerInvariant()) })
}

if ($definitions.Count -eq 0) {
    Write-Error "No integration definitions matched -Targets '$Targets'."
}

$statuses = New-Object System.Collections.Generic.List[object]
foreach ($definition in $definitions) {
    $statuses.Add((Get-IntegrationStatus -Name $definition.Name -RequiredEnvGroups $definition.Required))
}

$hasMissing = $false
foreach ($status in $statuses) {
    if ($status.Ready) {
        Write-Host ("[{0}] READY" -f $status.Name)
    }
    else {
        $hasMissing = $true
        Write-Host ("[{0}] MISSING" -f $status.Name)
        Write-Host ("  Missing env: {0}" -f ($status.Missing -join ", "))
    }
}

if ($DryRun) {
    Write-Host "[DryRun] Configuration validation finished. No external API calls were made."
    exit 0
}

if ($EnableSmoke) {
    Write-Host "[INFO] -EnableSmoke is on. Running minimal API smoke checks..."
    $smokeFailures = @(Invoke-SmokeChecks -Statuses $statuses)
    if ($FailOnSmokeError -and $smokeFailures.Count -gt 0) {
        Write-Error ("Smoke checks failed: {0}" -f ($smokeFailures -join ", "))
    }
}
else {
    Write-Host "[INFO] Smoke checks are disabled by default. Use -EnableSmoke to run optional API probes."
}

if ($EnableBusinessClosure) {
    Write-Host "[INFO] -EnableBusinessClosure is on. Running reversible business closure checks..."
    $businessFailures = @(Invoke-BusinessClosureChecks -Statuses $statuses)
    if ($FailOnSmokeError -and $businessFailures.Count -gt 0) {
        Write-Error ("Business closure checks failed: {0}" -f ($businessFailures -join ", "))
    }
}
else {
    Write-Host "[INFO] Business closure is disabled by default. Use -EnableBusinessClosure for reversible create/trigger probes."
}

if ($hasMissing) {
    Write-Error "Some integrations are not ready. Fill missing environment variables and retry."
}

Write-Host "[OK] External integration configuration is READY."
