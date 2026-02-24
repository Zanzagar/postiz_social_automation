/**
 * Gita Valley Content Calendar — Google Apps Script Setup
 *
 * Usage:
 * 1. Create a new Google Sheet
 * 2. Open Extensions > Apps Script
 * 3. Paste this entire script
 * 4. Run setupContentCalendar()
 * 5. Share the sheet with your n8n service account
 */

function setupContentCalendar() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName('Content Calendar');
  if (!sheet) {
    sheet = ss.insertSheet('Content Calendar');
  }

  // Column headers
  const headers = [
    'date',           // A
    'content_pillar', // B
    'raw_text',       // C
    'media_url',      // D
    'platforms_ig',   // E
    'platforms_fb',   // F
    'platforms_tt',   // G
    'platforms_th',   // H
    'platforms_li',   // I
    'status',         // J
    'caption_ig',     // K
    'caption_fb',     // L
    'caption_tt',     // M
    'caption_th',     // N
    'caption_li',     // O
    'postiz_ids',     // P
    'posted_at',      // Q
    'error_msg',      // R
  ];

  // Set headers
  const headerRange = sheet.getRange(1, 1, 1, headers.length);
  headerRange.setValues([headers]);
  headerRange.setFontWeight('bold');
  headerRange.setBackground('#4a86c8');
  headerRange.setFontColor('#ffffff');

  // Freeze header row
  sheet.setFrozenRows(1);

  // Column widths
  const widths = {
    1: 110,  // date
    2: 140,  // content_pillar
    3: 300,  // raw_text
    4: 250,  // media_url
    5: 30,   // platforms_ig (checkbox)
    6: 30,   // platforms_fb
    7: 30,   // platforms_tt
    8: 30,   // platforms_th
    9: 30,   // platforms_li
    10: 130, // status
    11: 250, // caption_ig
    12: 250, // caption_fb
    13: 250, // caption_tt
    14: 250, // caption_th
    15: 250, // caption_li
    16: 150, // postiz_ids
    17: 150, // posted_at
    18: 200, // error_msg
  };

  for (const [col, width] of Object.entries(widths)) {
    sheet.setColumnWidth(parseInt(col), width);
  }

  // Date format for column A (rows 2-500)
  sheet.getRange('A2:A500').setNumberFormat('yyyy-mm-dd');

  // Content pillar dropdown (column B)
  const pillarRule = SpreadsheetApp.newDataValidation()
    .requireValueInList([
      'Cow Life',
      'Farm Ops',
      'Community',
      'Kitchen',
      'Spiritual',
      'CTA',
    ])
    .setAllowInvalid(false)
    .build();
  sheet.getRange('B2:B500').setDataValidation(pillarRule);

  // Platform checkboxes (columns E-I)
  sheet.getRange('E2:I500').insertCheckboxes();

  // Status dropdown (column J)
  const statusRule = SpreadsheetApp.newDataValidation()
    .requireValueInList([
      'draft',
      'ready',
      'pending_approval',
      'approved',
      'posted',
      'error',
    ])
    .setAllowInvalid(false)
    .build();
  sheet.getRange('J2:J500').setDataValidation(statusRule);

  // Color-code auto-filled columns (K-R) as light gray
  sheet.getRange('K1:R1').setBackground('#6d9eeb');
  sheet.getRange('K2:R500').setBackground('#f3f3f3');

  // Platform header labels (short names above checkboxes)
  sheet.getRange('E1').setValue('IG');
  sheet.getRange('F1').setValue('FB');
  sheet.getRange('G1').setValue('TT');
  sheet.getRange('H1').setValue('TH');
  sheet.getRange('I1').setValue('LI');

  // Add sample rows
  const sampleData = [
    ['2026-03-01', 'Cow Life', 'Lakshmi the cow enjoying the morning sun in the pasture. She just had her calf last week!', '', true, true, true, true, false, 'draft', '', '', '', '', '', '', '', ''],
    ['2026-03-01', 'Kitchen', 'Fresh paneer made this morning from our own cows milk. Lunch prasadam prep in full swing.', '', true, true, false, true, false, 'draft', '', '', '', '', '', '', '', ''],
    ['2026-03-02', 'Spiritual', 'Morning mangal arati — the deities are decorated with fresh flowers from our garden.', '', true, true, true, true, true, 'draft', '', '', '', '', '', '', '', ''],
    ['2026-03-03', 'Farm Ops', 'Spring planting season begins! Our team is preparing 2 acres of organic vegetable beds.', '', true, true, true, false, true, 'draft', '', '', '', '', '', '', '', ''],
    ['2026-03-04', 'Community', 'Weekend volunteer day — 15 families came to help with the new greenhouse build.', '', true, true, true, true, false, 'draft', '', '', '', '', '', '', '', ''],
    ['2026-03-05', 'CTA', 'Join us for Sunday Feast this week! Farm-to-table vegetarian prasadam. All welcome.', '', true, true, false, true, false, 'draft', '', '', '', '', '', '', '', ''],
    ['2026-03-06', 'Cow Life', 'Our oxen Rama and Krishna pulling the plow for the first time this season. Traditional farming at its finest.', '', true, true, true, true, true, 'draft', '', '', '', '', '', '', '', ''],
    ['2026-03-07', 'Spiritual', 'Gaura Purnima festival preparations — the temple is alive with devotion and celebration.', '', true, true, true, true, true, 'draft', '', '', '', '', '', '', '', ''],
  ];

  if (sampleData.length > 0) {
    sheet.getRange(2, 1, sampleData.length, sampleData[0].length).setValues(sampleData);
  }

  // Add a Notes sheet with instructions
  let notesSheet = ss.getSheetByName('Instructions');
  if (!notesSheet) {
    notesSheet = ss.insertSheet('Instructions');
  }

  const instructions = [
    ['Gita Valley Content Calendar — Instructions'],
    [''],
    ['STAFF WORKFLOW:'],
    ['1. Fill in: date, content_pillar, raw_text, media_url'],
    ['2. Check the platform boxes (IG, FB, TT, TH, LI) for where to post'],
    ['3. Set status to "ready" when the row is complete'],
    ['4. Wait for AI-generated captions to appear (columns K-O)'],
    ['5. Review captions, then set status to "approved"'],
    ['6. The automation will post and update status to "posted"'],
    [''],
    ['COLUMN GUIDE:'],
    ['A: date — When to post (YYYY-MM-DD)'],
    ['B: content_pillar — Category (Cow Life, Farm Ops, Community, Kitchen, Spiritual, CTA)'],
    ['C: raw_text — Your description (1-3 sentences, plain language)'],
    ['D: media_url — Google Drive share link to image or video'],
    ['E-I: Platform checkboxes — Which platforms to post to'],
    ['J: status — Current state (draft → ready → pending_approval → approved → posted)'],
    ['K-O: AI captions — Auto-generated by the system (do not edit)'],
    ['P: postiz_ids — Post IDs from Postiz (auto-filled)'],
    ['Q: posted_at — When it was posted (auto-filled)'],
    ['R: error_msg — Error details if something went wrong (auto-filled)'],
    [''],
    ['NOTES:'],
    ['- Gray columns (K-R) are auto-filled by n8n. Do not edit them manually.'],
    ['- Media must be in a shared Google Drive folder with the service account.'],
    ['- One row = one piece of content (may post to multiple platforms).'],
  ];

  notesSheet.getRange(1, 1, instructions.length, 1).setValues(instructions);
  notesSheet.getRange(1, 1).setFontWeight('bold').setFontSize(14);
  notesSheet.getRange(3, 1).setFontWeight('bold');
  notesSheet.getRange(11, 1).setFontWeight('bold');
  notesSheet.getRange(24, 1).setFontWeight('bold');
  notesSheet.setColumnWidth(1, 700);

  SpreadsheetApp.getUi().alert('Content Calendar setup complete! Check the "Content Calendar" and "Instructions" tabs.');
}
