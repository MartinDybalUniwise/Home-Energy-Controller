# Step26 – zjištění mimo rozsah

- Původní test_sdg_log.py má tři reprodukovaná selhání: očekává registry sdg místo
  aktivního sdg_history a očekává dosud neimplementovanou prioritu SDG před FTE
  a označení fte_backup. Totéž reprodukováno na neměněném 3f0d9c2.
- Původní browser test_control_plan_english_catalog selhává po reloadu/jazykové
  změně; reprodukováno na neměněném 3f0d9c2 na samostatném mock preview :8182.
  Step26 nemění současnou volbu jazyka ani Control & Plan.
- Nasazená integrační větev obsahuje dřívější změny controllerů oproti main.
  Nesmí být přibaleny do Step26. Draft PR má integrační větev jako základ;
  před finálním merge do main je nutné vyřešit tuto předchozí integraci.

Tyto problémy nejsou opraveny, v souladu s výslovným omezením zadání.
Povinné kontroly se kvůli nim nepřeskakují a nejsou označeny PASS.
