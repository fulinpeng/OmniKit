const fs = require('fs');
const path = require('path');
const XLSX = require('xlsx');
const Docxtemplater = require('docxtemplater');
const PizZip = require('pizzip');
const puppeteer = require('puppeteer');
const mammoth = require('mammoth');
const { exec } = require('child_process');
const { promisify } = require('util');
const execAsync = promisify(exec);

// 配置文件路径
const EXCEL_PATH = './input/a3.xlsx'; // 使用已翻译的Excel文件
const TEMPLATE_PATH = './input/b2.docx';
const OUTPUT_DIR = './output';
const SHEET_NAME = 'Sheet1';

/**
 * 生成唯一的文件名，如果文件已存在则添加(2)、(3)等后缀
 * @param {string} baseFileName - 基础文件名（不含扩展名）
 * @returns {string} 唯一的文件名（不含扩展名）
 */
function generateUniqueFileName(baseFileName) {
    let uniqueFileName = baseFileName;
    let counter = 2;
    
    // 检查Word和PDF文件是否都不存在
    while (fs.existsSync(path.join(OUTPUT_DIR, uniqueFileName + '.docx')) || 
           fs.existsSync(path.join(OUTPUT_DIR, uniqueFileName + '.pdf'))) {
      uniqueFileName = `${baseFileName}(${counter})`;
      counter++;
    }
    
    return uniqueFileName;
  }

/**
 * 读取Excel文件数据
 */
function readExcelData() {
  console.log('正在读取Excel文件...');
  
  // 读取工作簿
  const workbook = XLSX.readFile(EXCEL_PATH);
  
  // 检查工作表是否存在
  if (!workbook.SheetNames.includes(SHEET_NAME)) {
    throw new Error(`工作表 "${SHEET_NAME}" 不存在！`);
  }
  
  // 读取指定工作表
  const worksheet = workbook.Sheets[SHEET_NAME];
  
  // 转换为JSON格式，专门处理中文编码
  const data = XLSX.utils.sheet_to_json(worksheet, { 
    header: 1, 
    raw: false,  // 不使用原始数据，让xlsx库处理数据类型
    defval: '', // 默认空值
    blankrows: true, // 保留空行
    cellText: false, // 使用单元格的显示文本
    cellHTML: false, // 不使用HTML格式
    cellNF: false,   // 不使用数字格式
    cellDates: true  // 正确处理日期
  });
  
  console.log(`成功读取 ${data.length - 1} 行数据`);
  
  return data;
}

/**
 * 将Excel列索引转换为数据
 * @param {Array} row - Excel行数据 (数组)
 * @param {string} columnLetter - 列字母 (如 'A', 'B', 'C'...)
 */
function getColumnValue(row, columnLetter) {
  // 将列字母转换为索引 (A=0, B=1, C=2...)
  const columnIndex = columnLetter.charCodeAt(0) - 'A'.charCodeAt(0);
  const value = row[columnIndex] || '';
  
  // 处理日期列 (J列)- 将Excel日期序列号转换为可读格式
  if (columnLetter === 'J' && typeof value === 'number') {
    return convertExcelDate(value);
  }
  
  // 确保返回的是正确的字符串格式，避免乱码
  if (typeof value === 'string') {
    return value.trim();
  } else if (typeof value === 'number') {
    return value.toString();
  } else {
    return String(value).trim();
  }
}

/**
 * 将Excel日期序列号转换为可读日期格式
 * @param {number} excelDate - Excel日期序列号
 * @returns {string} 格式化的日期字符串
 */
function convertExcelDate(excelDate) {
  try {
    // Excel日期序列号是从1900年1月1日开始计算的天数
    // 需要减去2天因为Excel的日期系统有个bug (1900年被当作闰年)
    const utc_days = Math.floor(excelDate - 25569);
    const utc_value = utc_days * 86400; // 86400秒 = 1天
    const date_info = new Date(utc_value * 1000);
    
    const year = date_info.getFullYear();
    const month = String(date_info.getMonth() + 1).padStart(2, '0');
    const day = String(date_info.getDate()).padStart(2, '0');
    
    return `${year}-${month}-${day}`;
  } catch (error) {
    // 如果转换失败，返回原始值
    return String(excelDate);
  }
}

/**
 * 从Excel行数据提取需要的字段，按顺序返回数组
 * @param {Array} row - Excel行数据
 * @returns {Array} 按照 A、F、E、A、B、D、C、E 顺序的数据数组
 */
function extractRowData(row) {
  const rawData = [
    getColumnValue(row, 'F'),  // 第1个数据：A列
    getColumnValue(row, 'H'),  // 第2个数据：F列
    getColumnValue(row, 'B'),  // 第3个数据：C列
    getColumnValue(row, 'F'),  // 第4个数据：E列
    getColumnValue(row, 'J'),  // 第5个数据：A列
    getColumnValue(row, 'E'),  // 第6个数据：B列
    getColumnValue(row, 'K'),  // 第7个数据：D列
    getColumnValue(row, 'B'),  // 第8个数据：C列
  ];
  
  // Excel文件已预先翻译，直接返回数据无需再次翻译
  rawData.forEach((value, index) => {
    console.log(`第${index + 1}个数据: "${value}"`);
  });
  
  return rawData;
}


/**
 * 处理单个Word文档 (使用更安全的方法)
 * @param {Buffer} templateBuffer - 模板文件Buffer
 * @param {Array} dataArray - 数据数组
 * @param {string} fileName - 文件名 (不含扩展名)
 */
async function processWordTemplate(templateBuffer, dataArray, fileName) {
  try {
    // Excel文件已预先翻译，所有数据应该都是英文
    // 但仍然检查是否有遗漏的中文字符
    const hasChinese = dataArray.some((value) => {
      const strValue = String(value || '').trim();
      return /[\u4e00-\u9fff]/.test(strValue);
    });
    
    // 使用最简单但最可靠的方法：直接字符串替换
    const zip = new PizZip(templateBuffer);
    let content = zip.files['word/document.xml'].asText();
    
    // 使用Buffer来处理中文字符，确保编码正确
    let modifiedContent = Buffer.from(content, 'utf8').toString('utf8');
    
    // 按顺序替换占位符，确保每个{0}都被正确替换
    let replaceCount = 0;
    let currentContent = modifiedContent;
    
    dataArray.forEach((value, index) => {
      // 确保值是字符串，特别处理中文字符
      let stringValue = String(value || '').trim();
      
      // 处理中文字符编码问题
      if (/[\u4e00-\u9fff]/.test(stringValue)) {
        // 确保中文字符正确编码，使用正确的UTF-8处理
        try {
          stringValue = decodeURIComponent(encodeURIComponent(stringValue));
        } catch (e) {
          // 如果编码失败，使用原始值
          stringValue = String(value || '').trim();
        }
      }
      
      // 查找第一个{0}并替换
      const placeholderIndex = currentContent.indexOf('{0}');
      if (placeholderIndex !== -1) {
        currentContent = currentContent.substring(0, placeholderIndex) + 
                        stringValue + 
                        currentContent.substring(placeholderIndex + 3);
        replaceCount++;
        console.log(`替换第${replaceCount}个{0}为: "${stringValue}"`);
      }
    });
    
    modifiedContent = currentContent;
    console.log(`总共替换了 ${replaceCount} 个占位符`);
    
    // 更新文档内容，使用正确的编码
    zip.files['word/document.xml']._data = Buffer.from(modifiedContent, 'utf8');
    
    // 生成新的文档
    const buffer = zip.generate({
      type: 'nodebuffer',
      compression: 'DEFLATE',
    });

    // 先保存Word文档
    const docxFileName = fileName + '.docx';
    const docxPath = path.join(OUTPUT_DIR, docxFileName);
    fs.writeFileSync(docxPath, buffer);
    
    console.log(`✓ 已生成Word文档: ${fileName}.docx`);
    
    // 如果发现中文字符，警告但继续转换
    if (hasChinese) {
      console.log(`⚠️ 警告: 数据中包含中文字符，可能翻译不完整: ${fileName}.docx`);
    }
    
    // 然后转换为PDF
    const pdfSuccess = await convertWordToPDF(docxPath, fileName);
    
    if (pdfSuccess) {
      console.log(`✓ 已生成PDF文档: ${fileName}.pdf`);
    }
    
    return pdfSuccess;
    
  } catch (error) {
    console.error(`✗ 处理 ${fileName} 时出错:`, error.message);
    return false;
  }
}

/**
 * 使用LibreOffice专业转换Word为PDF (保持完美格式)
 * @param {string} docxPath - Word文档路径
 * @param {string} fileName - 文件名 (不含扩展名)
 */
async function convertWordToPDFWithLibreOffice(docxPath, fileName) {
  try {
    console.log(`开始使用LibreOffice转换: ${fileName}.docx -> ${fileName}.pdf`);
    
    const outputDir = path.dirname(docxPath);
    const pdfPath = path.join(outputDir, fileName + '.pdf');
    
    // 使用LibreOffice命令行转换
    // --headless: 无界面模式
    // --convert-to pdf: 转换为PDF格式
    // --outdir: 输出目录
    // --norestore: 确保LibreOffice以干净状态启动，不恢复上次会话
    // --nodefault: 不加载默认文档
    const command = `"D:\\ruanjian\\libreOffice\\program\\soffice.exe" --headless --convert-to pdf --outdir "${outputDir}" --norestore --nodefault "${docxPath}"`;
    
    console.log(`执行命令: ${command}`);
    
    const { stdout, stderr } = await execAsync(command);
    
    if (stderr && !stderr.includes('INFO')) {
      console.warn(`LibreOffice警告: ${stderr}`);
    }
    
    console.log(`LibreOffice输出: ${stdout}`);
    
    // 检查PDF文件是否生成
    if (fs.existsSync(pdfPath)) {
      console.log(`✓ LibreOffice转换成功: ${fileName}.pdf`);
      return true;
    } else {
      throw new Error('PDF文件未生成');
    }
    
  } catch (error) {
    console.error(`LibreOffice转换失败: ${error.message}`);
    return false;
  }
}

/**
 * 备用方案：使用系统命令转换 (Windows)
 * @param {string} docxPath - Word文档路径
 * @param {string} fileName - 文件名 (不含扩展名)
 */
async function convertWordToPDFWithSystem(docxPath, fileName) {
  try {
    console.log(`尝试使用系统命令转换: ${fileName}.docx -> ${fileName}.pdf`);
    
    const outputDir = path.dirname(docxPath);
    const pdfPath = path.join(outputDir, fileName + '.pdf');
    
    // Windows系统尝试不同的命令
    const commands = [
      // 尝试用户安装的LibreOffice路径 (干净启动)
      `"D:\\ruanjian\\libreOffice\\program\\soffice.exe" --headless --convert-to pdf --outdir "${outputDir}" --norestore --nodefault "${docxPath}"`,
      // 尝试标准LibreOffice路径 (干净启动)
      `"C:\\Program Files\\LibreOffice\\program\\soffice.exe" --headless --convert-to pdf --outdir "${outputDir}" --norestore --nodefault "${docxPath}"`,
      // 尝试LibreOffice便携版 (干净启动)
      `"C:\\Program Files (x86)\\LibreOffice\\program\\soffice.exe" --headless --convert-to pdf --outdir "${outputDir}" --norestore --nodefault "${docxPath}"`,
      // 尝试OpenOffice (基础转换)
      `"C:\\Program Files (x86)\\OpenOffice 4\\program\\soffice.exe" --headless --convert-to pdf --outdir "${outputDir}" "${docxPath}"`
    ];
    
    for (const command of commands) {
      try {
        console.log(`尝试命令: ${command}`);
        const { stdout, stderr } = await execAsync(command, { timeout: 30000 });
        
        if (fs.existsSync(pdfPath)) {
          console.log(`✓ 系统命令转换成功: ${fileName}.pdf`);
          return true;
        }
      } catch (cmdError) {
        console.log(`命令失败: ${cmdError.message}`);
        continue;
      }
    }
    
    throw new Error('所有系统命令都失败');
    
  } catch (error) {
    console.error(`系统命令转换失败: ${error.message}`);
    return false;
  }
}

/**
 * 将Word文档转换为PDF (使用专业库)
 * @param {string} docxPath - Word文档路径
 * @param {string} fileName - 文件名 (不含扩展名)
 * @returns {boolean} 转换是否成功
 */
async function convertWordToPDF(docxPath, fileName) {
  console.log(`开始转换 ${fileName}.docx 为 PDF...`);
  
  // 方案1: 尝试使用LibreOffice专业转换
  let success = await convertWordToPDFWithLibreOffice(docxPath, fileName);
  
  if (!success) {
    console.log('LibreOffice转换失败，尝试系统命令...');
    // 方案2: 尝试系统命令转换
    success = await convertWordToPDFWithSystem(docxPath, fileName);
  }
  
  if (!success) {
    console.log(`❌ PDF转换失败: ${fileName}.docx`);
    console.log(`Word文档保留: ${fileName}.docx`);
  }
  
  return success;
}

/**
 * 备用方案：使用mammoth+puppeteer转换
 * @param {string} docxPath - Word文档路径
 * @param {string} fileName - 文件名 (不含扩展名)
 */
async function convertWordToPDFWithPuppeteer(docxPath, fileName) {
  try {
    // 使用mammoth转换为HTML
    const result = await mammoth.convertToHtml({ 
      path: docxPath,
      convertImage: mammoth.images.imgElement(function(image) {
        return image.read("base64").then(function(imageBuffer) {
          return {
            src: "data:" + image.contentType + ";base64," + imageBuffer
          };
        });
      })
    });
    
    let html = result.value;
    html = Buffer.from(html, 'utf8').toString('utf8');
    
    // 简化的HTML包装
    const fullHtml = `
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <style>
            body { 
                font-family: "Microsoft YaHei", "SimSun", Arial, sans-serif; 
                margin: 20px;
                line-height: 1.4;
            }
            img {
                max-height: 1em;
                vertical-align: baseline;
            }
        </style>
    </head>
    <body>
        ${html}
    </body>
    </html>`;
    
    // 使用Puppeteer生成PDF
    const browser = await puppeteer.launch({
      headless: 'new',
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    const page = await browser.newPage();
    await page.setContent(fullHtml, { waitUntil: 'networkidle0' });
    
    const pdfPath = path.join(OUTPUT_DIR, fileName + '.pdf');
    await page.pdf({
      path: pdfPath,
      format: 'A4',
      printBackground: true,
      margin: { top: '1cm', right: '1cm', bottom: '1cm', left: '1cm' }
    });
    
    await browser.close();
    
    console.log(`✓ 备用方案转换完成: ${fileName}.pdf`);
    
  } catch (error) {
    console.error(`备用方案转换失败: ${error.message}`);
    console.log(`Word文档仍然保留: ${fileName}.docx`);
  }
}


/**
 * 主函数
 */
async function main() {
  try {
    console.log('=== Excel转Word程序启动 (新版本-支持中文翻译)===\n');
    
    // 检查输入文件是否存在
    if (!fs.existsSync(EXCEL_PATH)) {
      throw new Error(`Excel文件不存在: ${EXCEL_PATH}`);
    }
    
    if (!fs.existsSync(TEMPLATE_PATH)) {
      throw new Error(`Word模板不存在: ${TEMPLATE_PATH}`);
    }
    
    // 确保输出目录存在
    if (!fs.existsSync(OUTPUT_DIR)) {
      fs.mkdirSync(OUTPUT_DIR, { recursive: true });
    } else {
      // 清理输出目录中的所有文件
      console.log('清理输出目录...');
      const files = fs.readdirSync(OUTPUT_DIR);
      files.forEach(file => {
        const filePath = path.join(OUTPUT_DIR, file);
        try {
          fs.unlinkSync(filePath);
          console.log(`删除: ${file}`);
        } catch (error) {
          console.log(`无法删除 ${file}:`, error.message);
        }
      });
      console.log('输出目录清理完成\n');
    }
    
    // 读取Excel数据
    const excelData = readExcelData();
    
    // 跳过第一行 (标题行)，自动识别有数据的行
    const allRows = excelData.slice(1); // 从第2行开始
    const dataRows = [];
    
    // 自动识别有数据的行 (B列不为空的行)
    let emptyRowCount = 0;
    const maxEmptyRows = 5; // 连续5行空行就认为数据结束
    
    for (let i = 0; i < allRows.length; i++) {
      const row = allRows[i];
      const bColumnValue = row[1]; // B列 (员工姓名列)
      
      // 如果B列有数据，则认为这一行有数据
      if (bColumnValue && String(bColumnValue).trim() !== '') {
        dataRows.push(row);
        emptyRowCount = 0; // 重置空行计数
      } else {
        emptyRowCount++;
        
        // 如果连续遇到太多空行，可能已经到数据末尾
        if (emptyRowCount >= maxEmptyRows) {
          console.log(`连续遇到 ${maxEmptyRows} 行空行，停止读取数据`);
          break;
        }
      }
    }
    
    // 读取Word模板
    const templateBuffer = fs.readFileSync(TEMPLATE_PATH);
    
    console.log('\n开始处理数据...\n');
    console.log(`自动识别到 ${dataRows.length} 行有效数据\n`);
    
    // 处理每一行数据
    let successCount = 0;
    let pdfSuccessCount = 0;
    let pdfFailedCount = 0;
    let pdfFailedFiles = [];
    
    for (let i = 0; i < dataRows.length; i++) {
      const row = dataRows[i];
      const actualRowNumber = i + 2; // 实际Excel行号 (从第2行开始)
      
      // 提取数据 (按照 A、F、E、A、B、D、C、E 顺序)
      const dataArray = extractRowData(row);
      const employeeName = dataArray[1]; // Employee Name 是第二个元素 (F列，索引1)
      
      // 生成文件名：A列_G列
      const aColumnValue = row[0]; // A列数据
      const gColumnValue = row[6]; // G列数据
      const baseFileName = `${String(aColumnValue || '').trim()}_${String(gColumnValue || '').trim()}`;
      
      // 生成唯一的文件名（处理重名）
      const fileName = generateUniqueFileName(baseFileName);
      
      // 如果文件名被修改了，提示用户
      if (fileName !== baseFileName) {
        console.log(`⚠️ 检测到重名文件，自动重命名: ${baseFileName} -> ${fileName}`);
      }
      
      // 调试：显示前几行的数据
      if (successCount < 3) {
        console.log(`\n=== 第 ${actualRowNumber} 行数据调试 ===`);
        console.log(`原始行数据长度:`, row.length);
        console.log(`A列: "${row[0]}" (类型: ${typeof row[0]})`);
        console.log(`F列: "${row[5]}" (类型: ${typeof row[5]})`);
        console.log(`G列: "${row[6]}" (类型: ${typeof row[6]})`);
        console.log(`E列: "${row[4]}" (类型: ${typeof row[4]})`);
        console.log(`B列: "${row[1]}" (类型: ${typeof row[1]})`);
        console.log(`D列: "${row[3]}" (类型: ${typeof row[3]})`);
        console.log(`C列: "${row[2]}" (类型: ${typeof row[2]})`);
        console.log(`提取并翻译后的数据数组:`, dataArray);
        console.log(`员工姓名: "${employeeName}"`);
        console.log(`生成的文件名: "${fileName}"`);
      }
      
      // 跳过空行或无员工姓名的行
      if (!employeeName || employeeName.trim() === '') {
        console.log(`跳过第 ${actualRowNumber} 行 (无员工姓名)`);
        continue;
      }
      
      // 处理Word文档
      const pdfSuccess = await processWordTemplate(templateBuffer, dataArray, fileName);
      successCount++;
      
      // 统计PDF转换结果
      if (pdfSuccess) {
        pdfSuccessCount++;
      } else {
        pdfFailedCount++;
        pdfFailedFiles.push(fileName);
      }
    }
    
    console.log(`\n=== 处理完成 ===`);
    console.log(`✅ 成功生成 ${successCount} 个Word文件`);
    console.log(`✅ 成功转换 ${pdfSuccessCount} 个PDF文件`);
    console.log(`❌ 转换失败 ${pdfFailedCount} 个文件 (包含翻译失败和PDF转换失败)`);
    console.log(`输出目录: ${path.resolve(OUTPUT_DIR)}`);
    
    // 显示转换失败的文件列表
    if (pdfFailedFiles.length > 0) {
      console.log(`\n=== 转换失败的文件列表 ===`);
      pdfFailedFiles.forEach((fileName, index) => {
        console.log(`${index + 1}. ${fileName}.docx`);
      });
      console.log(`\n💡 提示: 失败的文件已保留Word版本，可手动转换或检查转换工具配置`);
      console.log(`💡 翻译失败的文件已跳过PDF转换，但保留了Word文档`);
    }
    
  } catch (error) {
    console.error('程序执行出错:', error.message);
    process.exit(1);
  }
}

// 运行主函数
main();
