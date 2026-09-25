/**
 * 简历解析引擎（career_core / smartresume）后台切换页 i18n 字典。
 *
 * 抽离成独立模块以避免直接编辑并行 WIP 占用的 zh-CN.ts / en-US.ts（见项目 i18n 铁律）。
 * 在 locales/index.ts 中合并进 messages。
 */
export const RESUME_PARSER_ZH = {
  'pages.settings.ResumeParserEngine.s1': '简历解析引擎',
  'pages.settings.ResumeParserEngine.s2': '选择用于解析上传简历的本地开源引擎。切换后，后续上传的简历将使用所选引擎解析（数据不出本机）。',
  'pages.settings.ResumeParserEngine.s3': '解析引擎',
  'pages.settings.ResumeParserEngine.s4': 'Career Core（Rust 确定性引擎）',
  'pages.settings.ResumeParserEngine.s5': '本地 Rust 引擎，轻量、无网络、无需 GPU。适合结构化简历的确定性抽取。',
  'pages.settings.ResumeParserEngine.s6': 'SmartResume（阿里开源版面感知）',
  'pages.settings.ResumeParserEngine.s7': '阿里开源版面感知解析，含版面检测与小模型，抽取更丰富，但需单独部署（依赖较重）。',
  'pages.settings.ResumeParserEngine.s8': '注册状态',
  'pages.settings.ResumeParserEngine.s9': '已注册',
  'pages.settings.ResumeParserEngine.s10': '未注册',
  'pages.settings.ResumeParserEngine.s11': '可执行文件',
  'pages.settings.ResumeParserEngine.s12': '已就绪',
  'pages.settings.ResumeParserEngine.s13': '未就绪（需安装）',
  'pages.settings.ResumeParserEngine.s14': '重置',
  'pages.settings.ResumeParserEngine.s15': '保存',
  'pages.settings.ResumeParserEngine.s16': '设置已保存',
  'pages.settings.ResumeParserEngine.s17': '加载失败',
  'pages.settings.ResumeParserEngine.s18': '保存失败',
  'pages.settings.ResumeParserEngine.s19': '已重置为最近保存的设置',
  'pages.settings.ResumeParserEngine.s20': '该引擎后端已注册，但本机可执行文件未就绪，切换后解析将失败，请先完成部署。',
}

export const RESUME_PARSER_EN = {
  'pages.settings.ResumeParserEngine.s1': 'Resume Parser Engine',
  'pages.settings.ResumeParserEngine.s2': 'Choose the local open-source engine used to parse uploaded resumes. After switching, subsequently uploaded resumes will be parsed by the selected engine (data stays on-premise).',
  'pages.settings.ResumeParserEngine.s3': 'Parser Engine',
  'pages.settings.ResumeParserEngine.s4': 'Career Core (Rust deterministic engine)',
  'pages.settings.ResumeParserEngine.s5': 'Local Rust engine: lightweight, no network, no GPU. Deterministic extraction for structured resumes.',
  'pages.settings.ResumeParserEngine.s6': 'SmartResume (Alibaba open-source layout-aware)',
  'pages.settings.ResumeParserEngine.s7': 'Alibaba open-source layout-aware parser with layout detection and a small model for richer extraction, but requires separate deployment (heavier dependencies).',
  'pages.settings.ResumeParserEngine.s8': 'Registered',
  'pages.settings.ResumeParserEngine.s9': 'Registered',
  'pages.settings.ResumeParserEngine.s10': 'Not registered',
  'pages.settings.ResumeParserEngine.s11': 'Executable',
  'pages.settings.ResumeParserEngine.s12': 'Ready',
  'pages.settings.ResumeParserEngine.s13': 'Not ready (needs install)',
  'pages.settings.ResumeParserEngine.s14': 'Reset',
  'pages.settings.ResumeParserEngine.s15': 'Save',
  'pages.settings.ResumeParserEngine.s16': 'Settings saved',
  'pages.settings.ResumeParserEngine.s17': 'Load failed',
  'pages.settings.ResumeParserEngine.s18': 'Save failed',
  'pages.settings.ResumeParserEngine.s19': 'Reset to last saved settings',
  'pages.settings.ResumeParserEngine.s20': 'This engine is registered but its executable is not ready on this machine. Switching will cause parsing to fail until deployment is completed.',
}
