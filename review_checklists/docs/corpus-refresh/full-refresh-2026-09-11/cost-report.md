# Second Cost refresh - 2026-09-11

This separate round accounts for **all 226 baseline Cost canonical records and nine aliases**. It makes **27 content updates**, records **122 supported-unchanged guidance decisions**, and leaves **77 explicit needs-manual-review gaps**. A gap means current evidence is insufficient, not that the record is necessarily incorrect. No recommendation was added, deleted or merged.

**45 YAML files changed:** 27 content updates plus 18 mapping-only files. The 122 supported-unchanged outcomes describe guidance, not byte identity: 18 received provenance mappings while their guidance, identity, automation and query text stayed exact. There are 24 explicit upstream mappings on 22 canonicals; four content-updated records also received mappings. All 77 manual-review gaps remain byte-identical. In total, 181 files remain byte-identical to this round's baseline.

This is not exhaustive Azure Cost coverage, independent human approval, live Azure validation or proof of savings. Every baseline record has an explicit outcome and reason in [cost-refresh-manifest.json](cost-refresh-manifest.json); the outcome ledger below lists every GUID.

## Immutable history and round boundaries

The [first-stage manifest](../cost-refresh-manifest.json), [original research](../cost-research.json) and [nine-merge audit](../cost-alias-migration.json) remain immutable and hash-pinned by [cost-baseline.json](cost-baseline.json). The first refresh was 48 updates plus eight additions (227 to 235 Cost); the nine approved merges then produced 226 canonicals and nine aliases. This round preserves those 235 addressable identities. The historical regression tests now read the pinned post-merge baseline; the new Cost tests compare every live record and file hash against the exact second-round result.

| Starting cohort | Updated | Supported unchanged | Needs manual review | Total |
| --- | ---: | ---: | ---: | ---: |
| first-round-addition | 0 | 5 | 3 | 8 |
| first-round-update | 0 | 15 | 33 | 48 |
| previously-untouched-merge-survivor | 0 | 8 | 1 | 9 |
| truly-untouched-original | 27 | 94 | 40 | 161 |

Of the 161 truly untouched originals at round start, **27 were corrected, 94 had their guidance supported, and 40 remain explicitly unverified**. Rechecking an item against a narrow source is not a new approval of every inherited query or service detail.

## Technical changes

Nine Foundry/OpenAI fixes distinguish actual billing meters, reasoning/output budgets, Batch API economics and charged fine-tuned deployments. Seven Azure Files fixes distinguish provisioned v2, provisioned v1 and PAYG, including independent provisioning, snapshot overflow and soft-delete billing. Front Door fixes replace the invalid 204 probe shortcut with HEAD/200 and meaningful-health safeguards, and constrain single-origin probe removal. Other fixes cover Spot eviction semantics, disk reservation eligibility, VM rightsizing, Arm64 compatibility, AKS node sizing/KEDA and ML compute benchmarking. Blob version expiry retains approved recovery/retention prerequisites.

| Updated canonical GUID | Stable name | Reason |
| --- | --- | --- |
| `0d6d5b07-c475-408c-8f6a-fa8c92b96957` | `wafsg-ArchitecturalDesignDecisionsAzureOpenaiModels` | Avoid treating TPM/RPM alone as financial truth. |
| `550bf6a6-0fd6-4f5e-a447-fefda36067bc` | `wafsg-AzureOpenaiCompletionsApiDesignClientCode` | Replace legacy API-wide token parameter assumptions with the documented reasoning/output contract. |
| `73965cc9-1763-43c1-82aa-549b3ea75f4e` | `wafsg-AzureOpenaiPriceBreakpointsNextBillingPeriod` | Remove unsupported equal-cost image-count and universal hourly fine-tuning claims. |
| `3100afcf-2db1-4f14-901c-bd5e33bc29ff` | `wafsg-CostEfficiencyBatchRequests` | Distinguish the priced Batch deployment feature from generic grouping of requests. |
| `9e2fb33a-0e01-43c6-9de0-2409778ad08d` | `wafsg-PromptInputResponseLength` | Account for hidden reasoning and incomplete results instead of visible output alone. |
| `8c51bdd3-d4cb-4742-a323-89917c6ac87e` | `wafsg-ThroughputPricingModelRateOptimization` | Qualify a universal lower-cost assertion with utilization and actual meter evidence. |
| `a1abac7c-cce9-4443-97e8-2faf150559d4` | `wafsg-UnusedFineTunedModelsOngoingHostingFee` | Target the charged deployment lifecycle rather than indiscriminately deleting model assets. |
| `d310e9bc-ae3d-4eff-90a1-8356d72a1376` | `wafsg-UsageOptimizationTokenLimitingConstraints` | Correct a second distinct legacy token-limit control without merging identities. |
| `fb012775-b93d-442c-916c-81ca72d7bc91` | `wafsg-ViableCostModelCostManagement` | Extend the text-only model to the documented additional meters. |
| `393a040f-d329-4479-ab11-88b2c5a46ceb` | `revcl-InterruptibleJobsDiscountedPrice` | Replace the misleading bidding description with documented Spot pricing and eviction semantics. |
| `a6bcca2b-4fea-41db-b3dd-95d48c7c891d` | `revcl-LargerDisksTib` | Replace an incomplete size-only eligibility rule with actual SKU and consumption restrictions. |
| `544451e1-92d3-4442-a3c7-628637a551c5` | `revcl-Vms` | Make a terse sizing command actionable and retain human interpretation of inventory. |
| `620cb68e-2005-464b-90d3-0e767babcfcd` | `wafsg-ArmUbuntuAgentNodesArmArchitectureNodes` | Remove blanket architecture selection and correct the ambiguous ARM wording. |
| `afad2446-229b-4b5c-89fc-33e0a1ffdf05` | `wafsg-KubernetesEventDrivenAutoscalingKedaScalers` | Remove an aging scaler-count claim while retaining the guide's event-driven scaling recommendation. |
| `45c1b3bf-8e01-4337-984d-e8b03a969e4c` | `wafsg-RightVirtualMachineInstanceTypeHighPerformanceInstance` | Correct the inherited reversal that blamed powerful instances for undersizing problems. |
| `1d3deb66-a7cf-4c9e-8071-3b3e3d60c478` | `wafsg-VeryLargeMachinesSpecializedCoreInstructions` | Replace malformed HTML/encoding and an overly prescriptive static family list with the documented benchmark approach. |
| `3da1dae2-cc88-4147-8607-c1cca0e61465` | `revcl-DefaultHomepageinApplicationSettings` | Correct an unsafe 204-as-healthy cost shortcut against the current service contract. |
| `8dd458e9-2713-49b8-8110-2dbd6eaf11e6` | `revcl-MinimalContentFunctionProxy` | Replace an obsolete Function Proxy suggestion with the documented HEAD/200 contract. |
| `f397a438-b320-46f8-a41a-f94545db3412` | `wafsg-AzureFrontDoorOriginGroupSingleBackEndPools` | Add scope and monitoring safeguards and use the exact published Advisor opportunity as inventory. |
| `9dd18ccf-33eb-4da0-9710-7b3d64290faa` | `wafsg-CostEffectiveAccessTierTotalOverallCost` | Remove the unsupported majority-should-use-cool assumption and distinguish the billing model. |
| `54bceac0-695d-4d3a-9e50-91fdb4c9f51a` | `wafsg-FastDataTransferSpeedsAzureStandardHddStorage` | Separate media, protocol, resource model and billing dimensions. |
| `72af3409-f6b8-43b7-b254-31990577bb73` | `wafsg-LifecycleManagementPolicyOldBlobVersions` | Preserve cost intent while making deletion prerequisites explicit. |
| `bb6048c7-29fd-4388-aa22-de89fdbb39ea` | `wafsg-MinimumRecommendedRetentionPeriodPremiumFileShares` | Correct the inherited model-independent rate description and preserve recovery requirements. |
| `72b9477f-3c39-4633-a052-90b1203f9be5` | `wafsg-StandardAzureFileSharesPremiumFileShares` | Retain the documented migration advice only for the applicable PAYG model. |
| `f3dd18d1-9937-413e-99a6-6abbe25b574c` | `wafsg-StandardSmbAzureFileSharesSameStandardStorageHardware` | Scope an inherited standard-media tier rule to its actual billing model. |
| `220f8243-dcba-41cd-95c1-70b8b0cc3bd2` | `wafsg-StandardSmbFileSharesStandardFileShares` | Replace obsolete two-account-kind and one-share universal prescriptions. |
| `f3715e13-e5c7-4830-b1a0-4319523efab1` | `wafsg-TotalAzureFilesBillAzureFileSync` | Account for provisioned v2 snapshot inclusion/overflow instead of generalizing older billing. |

## Primary versus supplemental KQL

Primary query-bearing Cost records increased **31 to 34**, with **31 distinct final primary query texts**. Three new primary queries use the documented AdvisorResources Cost projection plus exact published recommendationTypeId filters: VM resize/shutdown, eligible managed-disk reservations and single-origin Front Door probes. None joins away subscription-level recommendations or infers IDs by text matching.

All 31 prior primary assignments retain exact text. The six historical supplemental-only variants remain documentation-only in [cost-research.json](../cost-research.json); this round adds no supplemental variants. Across both rounds there are 37 distinct catalog variants: 31 final unique primary texts and six supplemental-only texts. The app still executes only the single primary `queries.arg`.

Every new query is **inventory**, with `validatedAt: null`. No Azure execution or service-side compilation was performed. Review intended scope, read permissions, paging, Advisor freshness and dismissals, workload constraints, current prices and existing commitments. Missing/truncated rows are not a pass, and a recommendation row is neither a policy violation nor approval to change resources.

The complete three-query catalog, derivation and scope caveats are in [cost-sources.json](cost-sources.json). No query text was promoted to a semantic mapping automatically.

## Measured source scopes, not universal coverage

| Inventory | Distinct units | Full | Partial | Unmapped | Full percentage | Partial percentage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `waf-cost-checklist` | 14 | 1 | 11 | 2 | 7.14% | 78.57% |
| `advisor-cost-catalog` | 66 | 4 | 6 | 56 | 6.06% | 9.09% |

The denominators are only the **14 numbered WAF Cost checklist rows** and **66 entries in the published Advisor Cost catalog**. Partial is not full; unmapped means no explicit mapping was established in this Cost-only pass, not necessarily that the whole corpus lacks that control. No all-Azure or all-WAF-service-guide percentage is claimed.

[cost-source-coverage.json](cost-source-coverage.json) contains all upstream IDs, canonical mappings, semantic rationales, payload hashes and unknown entries. The current snapshots are [cost-waf-inventory.json](cost-waf-inventory.json) and [cost-advisor-inventory.json](cost-advisor-inventory.json). Both equal their shared pipeline snapshots exactly, including canonical source IDs `waf-cost-checklist` and `advisor-cost-catalog`. All 14 WAF and 66 Advisor item payloads and content hashes agree with the central inventories. Earlier parent-proposed draft names were corrected, not treated as separate or uncovered sources; the normalization record retains those previous names and the original central paths/file hashes. This naming correction changes no semantic assessment, query or coverage count.

No prior complete inventory was supplied, so this round does not label any upstream ID as programmatically new or removed. The dated inventories establish a baseline for future diffs.

## Known gaps and deferred actions

The 77 explicit gaps include service-specific claims not reverified in this round, including some first-round improvements whose original evidence remains preserved. High-priority examples are SAP HANA E-series certification and Standard SSD/HDD suitability; existing-disk shrinking; plan-specific Functions await billing; AKS node-pool stop, scale-down, MIG and snapshots; licensing/commerce eligibility; and exact Firewall SKU throughput. None received a blanket review stamp.

The old Azure OpenAI WAF guide redirects to a model catalog. That redirect was not treated as support for obsolete cost claims; the current Foundry billing, reasoning and Batch sources were used.

WAF CO:09 flow-priority costs and CO:13 personnel-time costs remain unmapped; check other pillars and aliases before proposing new controls. No cross-pillar duplicate or new control was asserted without evidence. The two prior App Gateway/ExpressRoute technically deferred merge pairs remain separate canonicals; this round did not perform any additional merge.

## Complete baseline outcome ledger

Evidence labels below resolve to the source index in [cost-sources.md](cost-sources.md). All exact before/after documents, changed fields, paths, reasons and hashes are in the baseline/manifest. `mapped` indicates an explicit upstream-ID assessment, independent of the content outcome.

| GUID | Stable name | Content outcome | Source evidence | Mapping |
| --- | --- | --- | --- | --- |
| `570cc0b7-8bcc-54bc-b0a3-abf24374c97b` | `cost-AdvisorActionBacklog` | supported_unchanged | advisor, finops | not assessed |
| `ccf66d9e-1364-576b-9b40-16f91a5b52b7` | `cost-WorkloadCostModelUnitEconomics` | supported_unchanged | waf | mapped |
| `ae757485-92a4-482a-8bc9-eefe6f5b5ec3` | `revcl-AgreementBillingRbacRoleAssignmentsMcaBillingAccount` | needs_manual_review | Explicit unverified gap | not assessed |
| `a491dfc4-9353-4213-9217-eef0949f9467` | `revcl-AzureRunCostsDevTestSystems` | needs_manual_review | Explicit unverified gap | not assessed |
| `6ad5c3dd-e5ea-4ff1-81a4-7886ff87845c` | `revcl-BillingAccountNotificationConfigureAgreement` | needs_manual_review | Explicit unverified gap | not assessed |
| `b65c878b-4b14-4f4e-92d8-d873936493f2` | `revcl-DatabaseManagementSystemExcessiveNetworkTraffic` | needs_manual_review | Explicit unverified gap | not assessed |
| `90e87802-602f-4dfb-acea-67c60689f1d7` | `revcl-EffectiveCostManagementInvoiceSections` | needs_manual_review | Explicit unverified gap | not assessed |
| `12cd499f-96e2-4e41-a243-231fb3245a1c` | `revcl-EnrollmentHierarchyDepartments` | needs_manual_review | Explicit unverified gap | not assessed |
| `5cf9f485-2784-49b3-9824-75d9b8bdb57b` | `revcl-EnterpriseDevTestSubscriptionsNonProductionWorkloads` | needs_manual_review | Explicit unverified gap | not assessed |
| `29fd366b-a180-452b-9bd7-954b7700c667` | `revcl-ForecastedBudgetAlertsActual` | supported_unchanged | waf | mapped |
| `e81a73f0-84c4-4641-b406-14db3b4d1f50` | `revcl-MicrosoftAzurePlanDevTestOffer` | needs_manual_review | Explicit unverified gap | not assessed |
| `685cb4f2-ac9c-4b19-9167-993ed0b32415` | `revcl-NotificationContactsGroupMailbox` | needs_manual_review | Explicit unverified gap | not assessed |
| `9877f353-2591-4e8b-8381-e9043fed1010` | `revcl-ProductionHanaDatabaseServerVmsSapHanaHardwareDirectory` | needs_manual_review | Explicit unverified gap | not assessed |
| `ff5136bd-dcf1-4d2b-ae52-39333efdf45a` | `revcl-SapHanaDatabaseBackupsAzureVms` | needs_manual_review | Explicit unverified gap | not assessed |
| `925d1f8c-01f3-4a67-948e-aabf0a1fad60` | `revcl-SapSystemStartStopCosts` | needs_manual_review | Explicit unverified gap | not assessed |
| `32952499-58c8-4e6f-ada5-972e67893d55` | `revcl-SetupCostReportingAzureCostManagement` | supported_unchanged | waf | mapped |
| `cafde29d-a0af-4bcd-87c0-0f299d63f0e8` | `revcl-SiteRecoveryMonitoring` | needs_manual_review | Explicit unverified gap | not assessed |
| `71dc00cd-4392-4262-8949-20c05e6c0333` | `revcl-StandardHddAzureStorageAzureStandardSsdStorage` | needs_manual_review | Explicit unverified gap | not assessed |
| `a24d0de3-d4b9-4dfb-8ddd-bbfaf123fa01` | `revcl-SupportRequestEscalationProcess` | needs_manual_review | Explicit unverified gap | not assessed |
| `5d82e6df-6f61-42f2-82e2-3132d293be3d` | `revcl-AzureLighthouseTenant` | needs_manual_review | Explicit unverified gap | not assessed |
| `6e043e2a-a359-4271-ae6e-205172676ae4` | `revcl-AzureVmwareSolutionInstances` | supported_unchanged | advisor | mapped |
| `4ba34d45-85e1-4213-abd7-bb012f7b95ef` | `revcl-GoodCostManagementProcessAzureCostManagement` | needs_manual_review | Explicit unverified gap | not assessed |
| `0c5365cb-838b-4dfb-9608-0bcfabe98460` | `wafsg-AppropriateAccountabilityProcessesCostManagementFeatures` | supported_unchanged | ai-cost | not assessed |
| `0d6d5b07-c475-408c-8f6a-fa8c92b96957` | `wafsg-ArchitecturalDesignDecisionsAzureOpenaiModels` | updated | ai-cost, ai-reasoning | not assessed |
| `550bf6a6-0fd6-4f5e-a447-fefda36067bc` | `wafsg-AzureOpenaiCompletionsApiDesignClientCode` | updated | ai-reasoning | not assessed |
| `73965cc9-1763-43c1-82aa-549b3ea75f4e` | `wafsg-AzureOpenaiPriceBreakpointsNextBillingPeriod` | updated | ai-cost | mapped |
| `3100afcf-2db1-4f14-901c-bd5e33bc29ff` | `wafsg-CostEfficiencyBatchRequests` | updated | ai-batch | not assessed |
| `6ebaa528-2e34-4366-b8cb-6bc3318ec624` | `wafsg-CostTrackingSystemModelUsage` | supported_unchanged | ai-cost | not assessed |
| `15ea2d47-0659-4906-a1ec-d26a00aa4237` | `wafsg-DifferentFineTuningCostsCostEfficiency` | supported_unchanged | ai-cost | not assessed |
| `e65920ea-b7aa-4eda-bfc8-36746c74933a` | `wafsg-MaximumTokenUsageLimitsDesiredApplicationPerformance` | supported_unchanged | ai-cost | not assessed |
| `9e2fb33a-0e01-43c6-9de0-2409778ad08d` | `wafsg-PromptInputResponseLength` | updated | ai-reasoning | not assessed |
| `25a3468e-92d0-4aa3-bb5f-c1214eee958b` | `wafsg-ProvisionManagedUtilizationThroughputUsage` | needs_manual_review | Explicit unverified gap | not assessed |
| `8c51bdd3-d4cb-4742-a323-89917c6ac87e` | `wafsg-ThroughputPricingModelRateOptimization` | updated | ai-cost, advisor | not assessed |
| `a1abac7c-cce9-4443-97e8-2faf150559d4` | `wafsg-UnusedFineTunedModelsOngoingHostingFee` | updated | ai-cost | not assessed |
| `48e39691-9809-4ab1-86fb-857d47e4163e` | `wafsg-UsageOptimizationAzureOpenai` | needs_manual_review | Explicit unverified gap | not assessed |
| `d310e9bc-ae3d-4eff-90a1-8356d72a1376` | `wafsg-UsageOptimizationTokenLimitingConstraints` | updated | ai-reasoning | not assessed |
| `fb012775-b93d-442c-916c-81ca72d7bc91` | `wafsg-ViableCostModelCostManagement` | updated | ai-cost, ai-reasoning | not assessed |
| `28856508-bfa7-5f94-82d8-7f6b53817bfe` | `cost-ManagedDiskSnapshotLifecycle` | needs_manual_review | Explicit unverified gap | not assessed |
| `c7acbe49-bbe6-44dd-a9f2-e87778468d55` | `revcl-AzureReservedInstancesSignificantCostSavings` | needs_manual_review | Explicit unverified gap | not assessed |
| `a2ed27b2-d186-4f1a-8252-bddde68a487c` | `revcl-DiskSizesGibDisk` | needs_manual_review | Explicit unverified gap | not assessed |
| `393a040f-d329-4479-ab11-88b2c5a46ceb` | `revcl-InterruptibleJobsDiscountedPrice` | updated | spot | not assessed |
| `a6bcca2b-4fea-41db-b3dd-95d48c7c891d` | `revcl-LargerDisksTib` | updated | disk-ri, advisor, finops | mapped |
| `7b95e06e-158e-42ea-9992-c2de6e2065b3` | `revcl-LearnMicrosoftAhub` | needs_manual_review | Explicit unverified gap | not assessed |
| `6e2065b3-a76a-4f4a-991e-8839ada46667` | `revcl-LicensePartDiscountTheVm` | needs_manual_review | Explicit unverified gap | not assessed |
| `6aae01e6-a84d-4e5d-b36d-1d92881a1bd5` | `revcl-LowerStorageTiersDisks` | needs_manual_review | Explicit unverified gap | not assessed |
| `59ae568b-a38d-4498-9e22-13dbd7bb012f` | `revcl-MeterCategoryLicensesWindowsVms` | needs_manual_review | Explicit unverified gap | not assessed |
| `92d34429-3c76-4286-97a5-51c5b04e4f18` | `revcl-PremiumSsdDisksStandardSsd` | needs_manual_review | Explicit unverified gap | not assessed |
| `b04e4f18-5438-47e5-aed1-26cd032af5b2` | `revcl-RecentSizesVm` | needs_manual_review | Explicit unverified gap | not assessed |
| `cb1f7d57-59ae-4568-aa38-d4985e2213db` | `revcl-RightSizingOptimization` | needs_manual_review | Explicit unverified gap | not assessed |
| `fc6998a5-35e3-4378-a7e3-1c67d68cf6a6` | `revcl-RightSizingVmsUsage` | supported_unchanged | vm | mapped |
| `64f9a19a-f29c-495d-94c6-c7919ca0f6c5` | `revcl-UnassociatedServicesIpAddresses` | needs_manual_review | Explicit unverified gap | not assessed |
| `2a119495-6d69-47dc-9a2e-d27b2d186f1a` | `revcl-VmDensityApplication` | needs_manual_review | Explicit unverified gap | not assessed |
| `75c1e945-b459-4837-bf7a-e7c6d3b475a5` | `revcl-VmFamiliesFlexibilityOption` | needs_manual_review | Explicit unverified gap | not assessed |
| `d0102cac-6aae-401e-9a84-de5de36d1d92` | `revcl-VmRightSizingAdvisor` | needs_manual_review | Explicit unverified gap | not assessed |
| `544451e1-92d3-4442-a3c7-628637a551c5` | `revcl-Vms` | updated | vm, advisor, finops | mapped |
| `ccbd9792-a6bc-4ca2-a4fe-a1dbf3dd95d4` | `revcl-VmssDemand` | supported_unchanged | vm | not assessed |
| `0a6605c5-2e42-4796-b60c-f2ac2a89872c` | `wafsg-AzureAutomationStartStopFeatureTheStartStopFeature` | needs_manual_review | Explicit unverified gap | not assessed |
| `8e136ca6-91e6-4cd0-8d19-b6cfec2622c1` | `wafsg-AzurePremiumSsdVDiskExtraCostOptimizationFeatures` | supported_unchanged | vm | not assessed |
| `e445d2d7-01a5-428d-9996-7d42b8727ae5` | `wafsg-BackupStorageCostsAzureBackupStorage` | supported_unchanged | vm | not assessed |
| `bf114ba8-d145-4e31-9798-fb07277a246d` | `wafsg-ComputeInfrastructureCostsSpotVirtualMachines` | supported_unchanged | vm | not assessed |
| `f7fc4792-bc2c-4a9d-98dc-ee637e18badd` | `wafsg-CostEffectiveApproachPriorityQueues` | supported_unchanged | vm | mapped |
| `389aca19-a7d5-4abb-82f6-66716e25023a` | `wafsg-CostGuardrailsGovernancePolicies` | supported_unchanged | waf | mapped |
| `12835f9e-fdcf-4ecd-8d96-22d2a32bbd29` | `wafsg-ParallelBatchProcessingJobsRightVmPlanSize` | supported_unchanged | vm | not assessed |
| `2a4a0772-4dab-4123-bdb0-569271e29b63` | `wafsg-PremisesWindowsServerOsLicensesAzureHybridBenefit` | supported_unchanged | vm | not assessed |
| `4f730d71-d8da-489b-b609-e9b1962ab07f` | `wafsg-PricingCalculatorBestVm` | supported_unchanged | vm | not assessed |
| `72eb7a10-acdd-47f4-ac63-c2366162dca0` | `wafsg-RightBillingModelCommitmentBasedModels` | supported_unchanged | vm | mapped |
| `9269756b-3f6f-4066-907b-a24ef20d44c9` | `wafsg-UnderutilizedVmsKeyApproach` | needs_manual_review | Explicit unverified gap | not assessed |
| `fd59590a-44b0-469a-aa57-e04183683d0b` | `wafsg-VmPlanSizesRightResources` | supported_unchanged | vm | not assessed |
| `c1b1cd52-1e54-4a29-a9de-39ac0e7c28dc` | `revcl-AksAutoscalerClustersUsage` | needs_manual_review | Explicit unverified gap | not assessed |
| `2b72a08b-0410-4cd6-9093-e068a5cf27e8` | `revcl-DevTestClusterNodepoolStart` | needs_manual_review | Explicit unverified gap | not assessed |
| `f82cb8eb-8c0a-4a63-a25a-4956eaa8dc4a` | `revcl-ExternalApplicationDifferentUsers` | needs_manual_review | Explicit unverified gap | not assessed |
| `87e651ea-bc4a-4a87-a6df-c06a4b570ebc` | `revcl-MultiInstancePartitioningGpuAksClusters` | needs_manual_review | Explicit unverified gap | not assessed |
| `64d1a846-e28a-4b6b-9a33-22a635c15a21` | `revcl-NodepoolSnapshots` | needs_manual_review | Explicit unverified gap | not assessed |
| `4d3dfbab-9924-4831-a68d-fdf0d72f462c` | `revcl-ScaleMode` | needs_manual_review | Explicit unverified gap | not assessed |
| `9cd3e427-64d5-48e8-aa6a-dfa7a473512c` | `wafsg-AppropriateManagedDiskTierWorkloadArchitectures` | supported_unchanged | aks | not assessed |
| `ec710c29-e6c0-4675-b051-73fc3a0010d7` | `wafsg-AppropriateVmSkuClusterArchitecture` | supported_unchanged | aks | not assessed |
| `620cb68e-2005-464b-90d3-0e767babcfcd` | `wafsg-ArmUbuntuAgentNodesArmArchitectureNodes` | updated | aks | not assessed |
| `3c328ad3-02b3-4b44-b833-e8e0edcf8fd8` | `wafsg-AzureManagedGrafanaContainerInsights` | needs_manual_review | Explicit unverified gap | not assessed |
| `8b20a125-f425-42b9-9636-128941325958` | `wafsg-AzureSavingsPlanAzureReservations` | supported_unchanged | aks | not assessed |
| `357e61fe-86e6-41c6-b446-3f0def6d8bcf` | `wafsg-AzureSpotVirtualMachinesUnutilizedAzureCapacity` | needs_manual_review | Explicit unverified gap | not assessed |
| `1104dc91-14f0-4330-ac7d-fa85039a0802` | `wafsg-CostAnalysisClusterExtensionAksCostAnalysis` | needs_manual_review | Explicit unverified gap | not assessed |
| `aa2243d7-e30a-4963-b569-a93bf2660bb2` | `wafsg-CostOptimizationOpportunitiesPerformanceMetrics` | supported_unchanged | aks | not assessed |
| `7bf19a02-eeec-4611-b559-f5cef964cc63` | `wafsg-CostSavingGoalsCloudFinancialDiscipline` | supported_unchanged | aks | mapped |
| `330a0b20-69f1-44b9-9b9e-907e8e1bf5ca` | `wafsg-ExcessResourceCapacityClusterArchitecture` | supported_unchanged | aks | not assessed |
| `ddb71774-895b-4149-9e0c-e348a9829df5` | `wafsg-ExtraNetworkingChargesClusterArchitecture` | supported_unchanged | aks | not assessed |
| `18dfc1c5-f5e8-4c89-9805-af9dd82f595d` | `wafsg-HorizontalPodAutoscalerOtherSelectMetrics` | supported_unchanged | aks | not assessed |
| `afad2446-229b-4b5c-89fc-33e0a1ffdf05` | `wafsg-KubernetesEventDrivenAutoscalingKedaScalers` | updated | aks | not assessed |
| `479e3bcb-48bb-4f49-a449-d67df3a82c1e` | `wafsg-PendingPodResourceRequirementsVmSkuSelection` | supported_unchanged | aks | not assessed |
| `45c1b3bf-8e01-4337-984d-e8b03a969e4c` | `wafsg-RightVirtualMachineInstanceTypeHighPerformanceInstance` | updated | aks | not assessed |
| `d6b9a1b1-66b9-4f32-9269-4dba8ff3691d` | `wafsg-UserRequestFailuresWorkloadArchitecture` | supported_unchanged | aks | not assessed |
| `ff159e4c-281f-4c30-aa1c-819ce3c94aad` | `wafsg-VerticalPodAutoscalerWorkloadArchitecture` | needs_manual_review | Explicit unverified gap | not assessed |
| `d917bb41-11ca-4487-a354-abad918096e6` | `wafsg-WorkloadArchitectureCluster` | supported_unchanged | aks | not assessed |
| `60822342-a88f-4260-a595-c5919386bbdd` | `wafsg-WorkloadArchitecturesDiskSize` | supported_unchanged | aks | not assessed |
| `cd463cbb-bc8a-4c29-aebc-91a43da1dae2` | `revcl-SpotVmsFallback` | needs_manual_review | Explicit unverified gap | not assessed |
| `577a5f04-5ce3-5bf2-be7b-28c1ec86f362` | `cost-CosmosIdleContainers` | supported_unchanged | advisor | mapped |
| `ed807702-4e85-5b2e-b191-3fc76fe70a60` | `cost-CosmosThroughputEconomics` | supported_unchanged | advisor | mapped |
| `a95b86ad-8840-48e3-9273-4b875ba18f20` | `revcl-DataCollectionRulesAzureMonitor` | needs_manual_review | Explicit unverified gap | not assessed |
| `674b5ed8-5a85-49c7-933b-e2a1a27b765a` | `revcl-DifferentLogAnalyticsWorkspacesDifferentRetention` | needs_manual_review | Explicit unverified gap | not assessed |
| `91be1f38-8ef3-494c-8bd4-63cbbac75819` | `revcl-PurgingLogPolicyColdStorage` | needs_manual_review | Explicit unverified gap | not assessed |
| `f846a556-0f24-45ba-a2e2-43855e78ca2d` | `wafsg-AzureReservedVirtualMachineInstancesNextOneToThreeYears` | supported_unchanged | ml | not assessed |
| `2905301e-e22b-4203-8fa0-6c7d740dd465` | `wafsg-CheaperVmSizesResourceUsage` | supported_unchanged | ml | mapped |
| `d02f1c6b-b32d-4027-8c23-dad429d06570` | `wafsg-EarlyTerminationPoliciesTrainingTerminationPolicies` | supported_unchanged | ml | not assessed |
| `af8c167c-be44-45c2-bb57-a1bc383a8abd` | `wafsg-IdleShutdownComputeInstances` | supported_unchanged | ml | not assessed |
| `f96f9439-c6c3-4bd1-a6ef-912307025375` | `wafsg-LessIterativeExperimentationComputeScaling` | supported_unchanged | ml | not assessed |
| `feac1256-41f0-435e-8d6c-c66c264deb5b` | `wafsg-LowerCostSkusUsageOptimization` | supported_unchanged | ml | not assessed |
| `8fff224b-1d7f-4116-8624-e92ed5afc67a` | `wafsg-LowPriorityVirtualMachinesBatchWorkloads` | supported_unchanged | ml | not assessed |
| `2c88452f-1c05-46c4-a541-54acbfc708b2` | `wafsg-MultipleSmallerInstancesTrainingWorkloads` | supported_unchanged | ml | not assessed |
| `bfc81863-3497-4a8d-a16e-aab55f3bae72` | `wafsg-NextOneToThreeYearsAzureReservedVmInstances` | supported_unchanged | ml | not assessed |
| `ac00077c-9c99-40f8-8b08-9938b9ab6445` | `wafsg-UsageOptimizationAppropriateResources` | supported_unchanged | ml | not assessed |
| `66c94617-9ee4-4b81-be7a-ef5dbd521fc6` | `wafsg-UsageOptimizationLowerLimits` | supported_unchanged | ml | not assessed |
| `42466537-fe74-483d-94b7-3525c15f3cf8` | `wafsg-UsageOptimizationResources` | supported_unchanged | ml | not assessed |
| `1d3deb66-a7cf-4c9e-8071-3b3e3d60c478` | `wafsg-VeryLargeMachinesSpecializedCoreInstructions` | updated | ml | not assessed |
| `d0c4b44f-7b43-428c-93f2-dedd7bf00799` | `wafsg-ApplicationGatewayInstanceCountAzureApplicationGateway` | supported_unchanged | appgw | not assessed |
| `7947e534-c9a8-435b-9e03-d300143b5f74` | `wafsg-ApplicationGatewayInstancesEmptyBackendPools` | needs_manual_review | Explicit unverified gap | not assessed |
| `3c5f0966-3c57-4e15-a6b0-6cb73405bbf1` | `wafsg-ApplicationGatewayInstancesExtraneousCosts` | supported_unchanged | appgw | not assessed |
| `6f1432ef-61d2-4037-8f85-58e005d16b8c` | `wafsg-AzureApplicationGatewayWebApplicationFirewall` | supported_unchanged | appgw | not assessed |
| `ac8bb190-71ba-48ec-9fef-351c1cd5501f` | `wafsg-CurrentCapacityUnitsforMicrosoftCostManagement` | supported_unchanged | appgw | not assessed |
| `74ad737c-cbb8-4e91-84b7-2aa937b37ede` | `wafsg-UnderutilizedResources` | supported_unchanged | appgw | not assessed |
| `e3cd59af-4664-4d35-b291-45076f5452bd` | `wafsg-AzureFirewallDeploymentsTestingEnvironments` | supported_unchanged | firewall | not assessed |
| `a8ac7739-8682-4369-84c6-e0fd8185f1a6` | `wafsg-AzureFirewallManagerOneFirewallAssociation` | supported_unchanged | firewall | not assessed |
| `e23cca89-b750-4a14-8187-038aa999ab81` | `wafsg-AzureFirewallSku` | supported_unchanged | firewall | not assessed |
| `9fba472e-101a-4d6c-b9e9-762ce0e6035d` | `wafsg-CostEffectiveApproachThirdPartySolutions` | supported_unchanged | firewall | not assessed |
| `5f8eaf16-cabf-4fc4-82f9-1b9069b3bac2` | `wafsg-FirewallInstancesUsageCostEffectiveness` | supported_unchanged | firewall | not assessed |
| `b68aec37-acbd-4101-be19-3e99e8d641f6` | `wafsg-FirewallUseWorkloads` | supported_unchanged | firewall | not assessed |
| `ed8185a5-8f3a-402b-bd40-a3db15b390fd` | `wafsg-LoggingRequirementsEstimate` | supported_unchanged | firewall | not assessed |
| `0648162b-e60c-4625-811d-8e844e53d297` | `wafsg-ManySpokeVirtualNetworksVirtualWanSecureHub` | supported_unchanged | firewall | not assessed |
| `c606fee7-9b75-4ce1-921f-aac5591768f8` | `wafsg-PermanentXAllocationInstances` | supported_unchanged | firewall | not assessed |
| `f91761cf-5135-4dc1-bebc-0f25ebd32c55` | `wafsg-ProperAzureFirewallSkuRightAzureFirewallSku` | needs_manual_review | Explicit unverified gap | not assessed |
| `c88ea77e-1e9c-4d30-8b5e-c5e35cd4d93f` | `wafsg-PublicIpAddressesNumber` | supported_unchanged | firewall | not assessed |
| `c6b65421-d9c6-46aa-85c5-9e891c888744` | `wafsg-TopFlowsLogFatFlows` | supported_unchanged | firewall | not assessed |
| `ef951ddc-d36a-4194-a039-48af1cd3b1dd` | `wafsg-UnusedAzureFirewallDeploymentsAzureFirewallInstances` | supported_unchanged | firewall | not assessed |
| `01e92d97-de38-46fd-a4b3-a180301ada9b` | `wafsg-UnusedPublicIpAddressesSnatPortUtilization` | supported_unchanged | firewall | not assessed |
| `f4e7926a-ec35-476e-a412-5dd17136bd62` | `revcl-CircuitsPeeringLocationLocalSku` | supported_unchanged | er | not assessed |
| `718cb437-b060-2589-8856-2e93a5c6633b` | `revcl-LocalAzureRegionsExpressrouteLocalCircuits` | supported_unchanged | er | not assessed |
| `7025b442-f6e9-4af6-b11f-c9574916016f` | `revcl-UnlimitedDataExpressrouteCircuitsBandwidth` | supported_unchanged | er | not assessed |
| `271b6cfe-4507-4afa-a1e5-000e3be105ac` | `wafsg-DeprovisionExpressrouteCircuitsUse` | needs_manual_review | Explicit unverified gap | not assessed |
| `a3aaf86d-0531-404f-b881-78bbacd912ca` | `wafsg-ExpressrouteCircuitSkuBandwidth` | supported_unchanged | er | not assessed |
| `c36e0c83-11b4-409a-a4a6-2118b52a380f` | `wafsg-ExpressrouteCircuitsUnnecessaryCost` | needs_manual_review | Explicit unverified gap | not assessed |
| `92eec823-61dd-486c-b46e-0339fc02987e` | `wafsg-ExpressroutePricingUnderstandPricing` | supported_unchanged | er | not assessed |
| `73967d95-39ff-47bb-b4f4-33ddade69d1f` | `wafsg-ExpressrouteVirtualNetworkGatewaySizePreferredVirtualNetworkGatewaySku` | needs_manual_review | Explicit unverified gap | not assessed |
| `edd459fa-3105-4a03-b009-4f983d23da5a` | `wafsg-MonitoringExpressrouteCostsExpressrouteCircuit` | supported_unchanged | er | not assessed |
| `c5c27eb1-6f1c-4b97-a216-0cbdc31a3c98` | `wafsg-ThreeDifferentSkuTypesUnlimitedDataPlan` | supported_unchanged | er | not assessed |
| `3da1dae2-cc88-4147-8607-c1cca0e61465` | `revcl-DefaultHomepageinApplicationSettings` | updated | frontdoor-probes | not assessed |
| `8dd458e9-2713-49b8-8110-2dbd6eaf11e6` | `revcl-MinimalContentFunctionProxy` | updated | frontdoor-probes | not assessed |
| `871b4651-734d-40f4-b8a5-1705fa30dbe3` | `wafsg-AzureFrontDoorIncomingRequests` | supported_unchanged | frontdoor | not assessed |
| `fc470281-721e-40db-9289-ad73b03159d7` | `wafsg-AzureFrontDoorInstanceDataTransferCosts` | supported_unchanged | frontdoor | not assessed |
| `f397a438-b320-46f8-a41a-f94545db3412` | `wafsg-AzureFrontDoorOriginGroupSingleBackEndPools` | updated | frontdoor, advisor, finops | mapped |
| `3db5b1f9-57ec-44a6-adec-4f7cef47e63c` | `wafsg-AzureFrontDoorReportsDataTransfer` | supported_unchanged | frontdoor | not assessed |
| `d16d79fc-3c0c-4da4-9cfe-8a6b97d7259d` | `wafsg-AzureFrontDoorRoutingMethod` | supported_unchanged | frontdoor | not assessed |
| `5ecb8da9-9b18-4f39-a69e-c69eb2513b4b` | `wafsg-AzureFrontDoorTiersRealisticCosts` | supported_unchanged | frontdoor | not assessed |
| `638db3b0-f9b3-49b8-86f1-11621086b10f` | `wafsg-BandwidthConsumptionFileCompression` | supported_unchanged | frontdoor | not assessed |
| `78f09072-d08f-430c-9d24-6d3b938ecd14` | `wafsg-HighAvailabilityRequirementsCentralizedServices` | supported_unchanged | frontdoor | mapped |
| `1069bc46-68c3-46dd-80d0-700866521165` | `wafsg-LongPeriodLoggingData` | supported_unchanged | frontdoor | not assessed |
| `7dd61623-a364-4a90-9eca-e48ebd54cd7d` | `revcl-CentralHubVirtualNetworkNetworkingServices` | needs_manual_review | Explicit unverified gap | not assessed |
| `45901365-d38e-443f-abcb-d868266abca2` | `revcl-BackupInstancesUnderlyingDatasource` | needs_manual_review | Explicit unverified gap | not assessed |
| `44be3b1a-27f8-4b9e-a1be-1f38df03a822` | `revcl-RecoveryPointsVaultArchive` | needs_manual_review | Explicit unverified gap | not assessed |
| `69bad37a-ad53-4cc7-ae1d-76667357c449` | `revcl-SiteRecoveryStorageMissionCriticalApplications` | needs_manual_review | Explicit unverified gap | not assessed |
| `c2efc5d7-61d4-41d2-900b-b47a393a040f` | `revcl-StandardSsdDisksReplicationThroughput` | needs_manual_review | Explicit unverified gap | not assessed |
| `4f3e4c7b-78e3-5170-8ef9-903de93cd563` | `cost-SqlDatabaseComputeModel` | needs_manual_review | Explicit unverified gap | not assessed |
| `82a6242d-ee75-51c0-bf02-bd357c422c30` | `cost-SqlEmptyElasticPools` | needs_manual_review | Explicit unverified gap | not assessed |
| `d7bb012f-7b95-4e06-b158-e2ea3992c2de` | `revcl-LearnMicrosoftPolicy` | needs_manual_review | Explicit unverified gap | not assessed |
| `d1e44a19-659d-4395-afd7-7289b835556d` | `revcl-LowerTierCustomizedRule` | supported_unchanged | blob | mapped |
| `dec4861b-c3bc-410a-b77e-26e4d5a3bec2` | `revcl-StandardSsdPremium` | needs_manual_review | Explicit unverified gap | not assessed |
| `d3294798-b118-48b2-a5a4-6ceb544451e1` | `revcl-StorageAccountsHotTier` | supported_unchanged | blob | not assessed |
| `c4e2436b-1336-4db5-9f17-960eee0bdf5c` | `revcl-StorageAccountsTransactionCharges` | supported_unchanged | blob | not assessed |
| `7e31c67d-68cf-46a6-8a11-94956d697dc3` | `revcl-TiersLess` | supported_unchanged | blob | not assessed |
| `4ee9e348-ad55-46c9-bdbf-e17adcae5fd0` | `wafsg-AppropriateLogStorageLocationAzureMonitorLogsWorkspace` | supported_unchanged | blob | not assessed |
| `e53d71d3-879f-4a64-b425-e30f007e7221` | `wafsg-AppropriatePricingPageAppropriateSettings` | supported_unchanged | blob | not assessed |
| `c1f59c13-a5f1-4969-a1f4-a3180d9f7a30` | `wafsg-AzurePricingCalculatorAzureFilesPricing` | supported_unchanged | files | not assessed |
| `4d17df43-4382-430a-9463-13abf73774d0` | `wafsg-AzurePricingCalculatorVariousRegions` | supported_unchanged | blob | not assessed |
| `5bf631db-5818-4a48-9bb2-12383fb22c27` | `wafsg-BillingModelCommitmentBasedModel` | supported_unchanged | blob | not assessed |
| `d48626ce-bf57-4b9a-92b4-58d2904aca16` | `wafsg-CoolerAccessTiersWarmerAccessTiers` | supported_unchanged | blob | not assessed |
| `18f1f2f6-de79-405d-b7a1-65fb571c0493` | `wafsg-CostAnalysisPaneAzurePortal` | supported_unchanged | blob | not assessed |
| `9dd18ccf-33eb-4da0-9710-7b3d64290faa` | `wafsg-CostEffectiveAccessTierTotalOverallCost` | updated | files | not assessed |
| `d78ebd83-3708-43dc-a146-c87c0bc845cc` | `wafsg-CostEffectiveDefaultAccessTierDefaultAccessTierSetting` | supported_unchanged | blob | not assessed |
| `96e18bc5-92d9-4184-990e-0916f7c116fa` | `wafsg-DefaultAccessTierRedundancyLevel` | supported_unchanged | blob | not assessed |
| `d8225b92-cc37-400e-9e24-660b9f4c1a28` | `wafsg-DefaultAccessTierSettingLifecycleManagementPolicies` | supported_unchanged | blob | not assessed |
| `ab60898d-c5ae-4087-95ce-5b55ed006972` | `wafsg-EmergencyDataRestorationSituationsStandardPriorityRehydration` | supported_unchanged | blob | not assessed |
| `a97cd83a-ed73-43df-bf01-11853e14f665` | `wafsg-EncryptionScopesUnnecessaryCharges` | supported_unchanged | blob | not assessed |
| `54bceac0-695d-4d3a-9e50-91fdb4c9f51a` | `wafsg-FastDataTransferSpeedsAzureStandardHddStorage` | updated | files | not assessed |
| `1e8c6cb4-abe1-4ba1-899f-5ddc0d700517` | `wafsg-HigherDataTransferCostsFewerLargeFiles` | supported_unchanged | blob | not assessed |
| `72af3409-f6b8-43b7-b254-31990577bb73` | `wafsg-LifecycleManagementPolicyOldBlobVersions` | updated | blob, waf | not assessed |
| `f455ac95-f1e3-4a9a-9fab-044e7faeff2f` | `wafsg-MetadataStorageChargesAzureFilesReservations` | needs_manual_review | Explicit unverified gap | not assessed |
| `bb6048c7-29fd-4388-aa22-de89fdbb39ea` | `wafsg-MinimumRecommendedRetentionPeriodPremiumFileShares` | updated | files | not assessed |
| `edc3f7bc-6b6c-41a8-8f11-1485781fdf58` | `wafsg-MinimumRecommendedRetentionPeriodShortRetentionPeriod` | supported_unchanged | blob | not assessed |
| `d48bcd05-e5af-4500-b04e-e35dce0f17f9` | `wafsg-NumerousLogFilesCostEffectiveAccessTiers` | supported_unchanged | blob | not assessed |
| `318fe019-cffa-4ca1-aa56-e00d1df86fe2` | `wafsg-OtherCostAspectsAzureFileSync` | supported_unchanged | files | not assessed |
| `11b05f06-7a9a-4f25-9816-f41f893897b4` | `wafsg-PremiumFileSharesIoPerformanceCharacteristics` | supported_unchanged | files | not assessed |
| `a5675d94-de9f-44b1-8b21-f8032cdf3f3d` | `wafsg-RoleBasedAccessControlResourceGroups` | supported_unchanged | blob | not assessed |
| `dd86bdc7-a08c-4624-9028-e0e80335a9ba` | `wafsg-SftpSupportSftpEndpoint` | supported_unchanged | blob | not assessed |
| `ccbe2ffd-7bea-41ce-93fa-a9facc5bc5d0` | `wafsg-SoftDeleteAdditionalTransaction` | supported_unchanged | blob | not assessed |
| `322c5ad8-8c4a-4aa9-acd7-6f34a3e47c9c` | `wafsg-SshFileTransferProtocolChangeFeedSupport` | supported_unchanged | blob | not assessed |
| `72b9477f-3c39-4633-a052-90b1203f9be5` | `wafsg-StandardAzureFileSharesPremiumFileShares` | updated | files | not assessed |
| `6a667592-f9c4-45ba-81c8-bb4841aa8781` | `wafsg-StandardAzureFileSharesPremiumShares` | supported_unchanged | files | not assessed |
| `f3dd18d1-9937-413e-99a6-6abbe25b574c` | `wafsg-StandardSmbAzureFileSharesSameStandardStorageHardware` | updated | files | not assessed |
| `220f8243-dcba-41cd-95c1-70b8b0cc3bd2` | `wafsg-StandardSmbFileSharesStandardFileShares` | updated | files | not assessed |
| `4fb53237-e44f-4292-a7a5-f8e79d55fc4e` | `wafsg-StorageCapacityChargesSeparateStorageAccount` | supported_unchanged | blob | not assessed |
| `f3715e13-e5c7-4830-b1a0-4319523efab1` | `wafsg-TotalAzureFilesBillAzureFileSync` | updated | files | not assessed |
| `a294f2dd-cd4f-42f7-80d8-798759c799e4` | `wafsg-UnderusedStorageAccountsCostEffectiveAccessTiers` | supported_unchanged | files | not assessed |
| `35e33789-7e31-4c67-b68c-f6a62a119495` | `revcl-AdditionalDataAnalysisCostData` | needs_manual_review | Explicit unverified gap | not assessed |
| `ee0bdf5c-c2ef-4c5d-961d-41d2500bb47a` | `revcl-AzureSynapseCommitUnitsAzureSynapseAnalyticsCosts` | needs_manual_review | Explicit unverified gap | not assessed |
| `6d697dc3-a2ed-427b-8d18-6f1a1252bddd` | `revcl-DedicatedSqlPoolCosts` | needs_manual_review | Explicit unverified gap | not assessed |
| `d5a3bec2-c4e2-4436-a133-6db55f17960e` | `revcl-MultipleApacheSparkPoolDefinitionsVariousSizes` | needs_manual_review | Explicit unverified gap | not assessed |
| `e68a487c-dec4-4861-ac3b-c10ae77e26e4` | `revcl-ServerlessApacheSparkAutomaticPauseFeatureTimeoutValue` | supported_unchanged | advisor | mapped |
| `54387e5c-ed12-46cd-832a-f5b2fc6998a5` | `revcl-SpendingAnomaliesOverspendingRisks` | supported_unchanged | waf, er | not assessed |
| `fe224a34-ae94-57de-8570-e8bae87812f7` | `cost-AppServiceEmptyPlans` | supported_unchanged | advisor | mapped |
| `ad53cc7d-e2e8-4aaa-a357-1549ab9153d8` | `revcl-FunctionAppsPlan` | needs_manual_review | Explicit unverified gap | not assessed |
| `0e7c28dc-9366-4572-82bf-f4564b0d934a` | `revcl-Functions` | needs_manual_review | Explicit unverified gap | not assessed |
| `27139b82-1102-4dbd-9eaf-11e6f843e52f` | `revcl-FunctionsData` | needs_manual_review | Explicit unverified gap | not assessed |
| `9f89dc7b-44be-43b1-a27f-8b9e91be1f38` | `revcl-GbSecondCalculationAsyncOperation` | needs_manual_review | Explicit unverified gap | not assessed |
| `cc881470-607c-41cc-a0e6-14658dd458e9` | `revcl-ReuseConnectionsFunctions` | needs_manual_review | Explicit unverified gap | not assessed |
| `359c363e-7dd6-4162-9a36-4a907ebae38e` | `revcl-SeparateConsumptionPlanHigherPlan` | needs_manual_review | Explicit unverified gap | not assessed |
| `4722d928-c1b1-4cd5-81e5-4a29b9de39ac` | `revcl-SingleZipFileColdStarts` | needs_manual_review | Explicit unverified gap | not assessed |
| `a14a3b78-26d3-4159-975b-df8e82c9590e` | `wafsg-AppServicePlanAzureMonitor` | supported_unchanged | app | not assessed |
| `dc84dbbc-6816-48ae-9926-e52e68d4273e` | `wafsg-AppServicePlanLowerEnvironments` | supported_unchanged | app | not assessed |
| `1572941a-e08a-4d0c-bae6-5af048bbcc2a` | `wafsg-AppServicePlanPremiumVTier` | needs_manual_review | Explicit unverified gap | not assessed |
| `66723d3b-34de-4f55-8861-299453c5b6d8` | `wafsg-AppServicePlansMultipleApplications` | supported_unchanged | app | not assessed |
| `692ab2db-ff92-44e9-ae54-910c66389e0d` | `wafsg-ConsistentUsagePatternDedicatedComputeInstances` | supported_unchanged | app | mapped |
| `83127c0d-df6c-4785-be24-e54d0933118d` | `wafsg-CostAnalysisToolAppServiceResources` | supported_unchanged | app | not assessed |
| `551337b1-cb7a-4f60-870b-331efa943936` | `wafsg-EachAppServiceTierAzurePricingCalculator` | supported_unchanged | app | not assessed |
| `4e2a03a6-ff51-46c5-902d-3d7161d9c99c` | `wafsg-EnvironmentCostsPreProductionEnvironments` | supported_unchanged | app | mapped |
| `b7564349-7885-4f66-89ae-b732adaf29ae` | `wafsg-ExtendedDataRetentionPeriodsExpensiveStorageTiers` | supported_unchanged | app | not assessed |
| `7ce7bbb5-df18-4e4d-86b6-83e25e835457` | `wafsg-GatewayAggregationPatternImplementDesignPatterns` | supported_unchanged | app | not assessed |
| `41026085-4728-4bff-abbe-be08a46e4735` | `wafsg-SameComputeEnvironmentProductionInstance` | supported_unchanged | app | not assessed |
| `289a2a9d-eda1-4be4-af63-23d230194724` | `wafsg-ScalingStrategyPreciseMaximum` | supported_unchanged | app | not assessed |
| `84808948-46c4-4cd5-aa74-b79826a19b32` | `wafsg-SuboptimalSkuSelectionAppServicePlan` | needs_manual_review | Explicit unverified gap | not assessed |

## Validation

Validation passed: **82 tests** across the new live Cost suite, strict historical Cost suite, shared corpus contract, merges and source coverage. `python -m review_checklists corpus validate` validated **2,011 recommendations and their aliases**; `python -m scripts.validate_corpus --root v2` validated **2,011 recommendations and nine checklists**. These global counts are an observation during concurrent pillar work, not a Cost-owned change or a hard-coded test expectation. Cost remains exactly **226 canonicals and nine aliases**.
