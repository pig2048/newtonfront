
from playwright.async_api import async_playwright

import sys
import asyncio
import traceback
import time
import hashlib
import random
import string
import requests
import json
import os


def requestHeader(appId, secretKey):
    nonceId = generateNonceId()
    md5Str = md5Encode(nonceId, appId, secretKey)
    return {
        'X-Api-Id': appId,
        'Authorization': md5Str,
        'X-Nonce-Id': nonceId
    }



def generateRandom(length=6):
    characters = string.ascii_letters + string.digits
    random_string = ''.join(random.choice(characters) for _ in range(length))
    return random_string



def generateNonceId():
    return str(int(time.time()* 1000)) + generateRandom()



def md5Encode(nonceId, appId, secretKey):
    md5 = hashlib.md5()
    md5.update((appId + nonceId + secretKey).encode('utf-8'))
    return md5.hexdigest()



def postRequest(url, data, headers):
    headers['Content-Type'] = 'application/json'
    return requests.post(url, json=data, headers=headers)



def getRequest(url, headers):
    return requests.get(url, headers=headers)



def load_config():
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except Exception as e:
        print(f"加载配置文件失败: {str(e)}")
        sys.exit(1)



def load_environments():
    try:
        with open('env.json', 'r', encoding='utf-8') as f:
            env_config = json.load(f)
        return env_config['environments']
    except Exception as e:
        print(f"加载环境配置文件失败: {str(e)}")
        sys.exit(1)


async def main():
    try:
        
        config = load_config()
        environments = load_environments()
        
        
        api_config = config['api']
        APPID = api_config['appId']
        SECRETKEY = api_config['secretKey']
        BASEURL = api_config['baseUrl']
        
        
        concurrency_config = config['concurrency']
        max_instances = concurrency_config['maxInstances']
        delay_between_start = concurrency_config['delayBetweenStartMs'] / 1000  
        
        
        rounds_config = config['rounds']
        delay_between_rounds = rounds_config['delayBetweenRoundsSeconds']
        
        
        total_environments = len(environments)
        total_rounds = (total_environments + max_instances - 1) // max_instances  
        
        print(f"环境总数: {total_environments}, 并发数: {max_instances}, 需要执行 {total_rounds} 轮")
        
        
        try:
            start_round = int(input(f"请输入起始轮次 (1-{total_rounds}，默认为1): ") or "1")
            if start_round < 1 or start_round > total_rounds:
                print(f"输入的起始轮次超出范围，将使用默认值1")
                start_round = 1
                
            remaining_rounds = total_rounds - start_round + 1
            exec_rounds = int(input(f"请输入要执行的轮数 (1-{remaining_rounds}，默认为{remaining_rounds}): ") or str(remaining_rounds))
            if exec_rounds < 1 or exec_rounds > remaining_rounds:
                print(f"输入的执行轮数超出范围，将使用默认值{remaining_rounds}")
                exec_rounds = remaining_rounds
                
            end_round = start_round + exec_rounds - 1
            if end_round > total_rounds:
                end_round = total_rounds
                
            print(f"\n将从第 {start_round} 轮开始，执行到第 {end_round} 轮，共 {exec_rounds} 轮")
        except ValueError:
            print("输入格式错误，将使用默认设置")
            start_round = 1
            end_round = total_rounds
            exec_rounds = total_rounds
        
        
        for round_num in range(start_round, end_round + 1):
            print(f"\n====== 开始执行第 {round_num}/{total_rounds} 轮任务 ======\n")
            
            
            start_idx = (round_num - 1) * max_instances
            end_idx = min(round_num * max_instances, total_environments)
            
            print(f"本轮处理环境索引范围: {start_idx} 到 {end_idx-1}")
            
            
            tasks = []
            for i in range(start_idx, end_idx):
                env = environments[i]
                tasks.append(run_instance(env['uniqueId'], env['envId'], APPID, SECRETKEY, BASEURL))
                
                await asyncio.sleep(delay_between_start)
            
            
            await asyncio.gather(*tasks)
            
            
            print("\n所有实例任务已完成，正在关闭环境...")
            close_tasks = []
            for i in range(start_idx, end_idx):
                env = environments[i]
                close_tasks.append(closeEnv(env['envId'], env['uniqueId'], APPID, SECRETKEY, BASEURL))
            
            
            await asyncio.gather(*close_tasks)
            print(f"第 {round_num} 轮所有环境已关闭")
            
            
            if round_num < total_rounds:
                print(f"等待 {delay_between_rounds} 秒后开始下一轮...")
                await asyncio.sleep(delay_between_rounds)
        
        print("\n====== 所有轮次任务已完成 ======\n")
        
    except Exception as e:
        error_message = traceback.format_exc()
        print('运行错误: ' + error_message)



async def closeEnv(envId, uniqueId, appId, secretKey, baseUrl):
    try:
        print(f"开始关闭实例 (uniqueId={uniqueId}, envId={envId})")
        requestPath = baseUrl + '/api/env/close'
        data = {
            'envId': envId,
            'uniqueId': uniqueId
        }
        headers = requestHeader(appId, secretKey)
        response = postRequest(requestPath, data, headers).json()

        if response['code'] != 0:
            print(f"实例 {uniqueId} 关闭失败: {response['msg']}")
            return False
        
        print(f"实例 {uniqueId} 关闭成功")
        return True
    except Exception as e:
        errorMessage = traceback.format_exc()
        print(f"实例 {uniqueId} 关闭出错: {errorMessage}")
        return False



async def run_instance(uniqueId, envId, appId, secretKey, baseUrl):
    try:
        print(f"开始启动实例 (uniqueId={uniqueId}, envId={envId})")
        debugUrl = await startEnv(envId, uniqueId, appId, secretKey, baseUrl)
        print(f"实例 {uniqueId} - 调试URL: {debugUrl}")

        async with async_playwright() as p:
            browser, context = await connectBrowser(p, debugUrl)
            await operationEnv(context)
        
        return True
    except Exception as e:
        errorMessage = traceback.format_exc()
        print(f'实例 {uniqueId} 运行错误: ' + errorMessage)
        return False



async def connectBrowser(playwright, debugUrl):
    chrome = playwright.chromium
    browser = await chrome.connect_over_cdp(f"http://{debugUrl}")
    
    contexts = browser.contexts
    if not contexts:
        context = await browser.new_context()
    else:
        context = contexts[0]
    
    
    pages = context.pages
    current_page = pages[0] if pages else await context.new_page()
    
    print(current_page.url)
    return browser, context


async def startEnv(envId, uniqueId, appId, secretKey, baseUrl):
    requestPath = baseUrl + '/api/env/start'
    data = {
        'envId': envId,
        'uniqueId': uniqueId
    }
    headers = requestHeader(appId, secretKey)
    response = postRequest(requestPath, data, headers).json()

    if response['code'] != 0:
        print(response['msg'])
        print('please check envId')
        sys.exit()

    port = response['data']['debugPort']
    print('env open result:', response['data'])
    return '127.0.0.1:' + port



async def operationEnv(context):
    page = await context.new_page()
    
    
    print("正在访问 Newton 奖励页面...")
    try:
        
        await page.goto('https://www.magicnewton.com/portal/rewards', timeout=60000)
        print("页面导航完成")
        
        
        try:
            await page.wait_for_load_state('domcontentloaded', timeout=10000)
        except Exception as e:
            print(f"等待页面加载状态超时，但继续执行: {str(e)}")
        
        
        print("等待页面渲染...")
        await asyncio.sleep(3)
        
        
        print("尝试使用XPath定位'Play now'按钮...")
        
        play_now_clicked = False
        try:
            
            xpath_selector = "//p[normalize-space()='Play now']"
            play_button = await page.wait_for_selector(xpath_selector, timeout=5000, state="visible")
            if play_button:
                print("使用XPath找到'Play now'按钮，准备点击...")
                await play_button.click()
                print("已点击'Play now'按钮")
                play_now_clicked = True
            else:
                raise Exception("未找到按钮")
        except Exception as e1:
            print(f"使用XPath点击按钮失败: {str(e1)}")
            
            
            try:
                print("尝试查找包含'Play now'文本的父元素...")
                
                
                result = await page.evaluate('''() => {
                    const elements = Array.from(document.querySelectorAll('p')).filter(el => el.textContent.trim() === 'Play now');
                    if (elements.length > 0) {
                        
                        let clickTarget = elements[0];
                        
                        while (clickTarget && clickTarget.tagName !== 'BODY') {
                            if (clickTarget.tagName === 'BUTTON' || clickTarget.tagName === 'A') {
                                break;
                            }
                            clickTarget = clickTarget.parentElement;
                        }
                        if (clickTarget) {
                            clickTarget.click();
                            return true;
                        }
                    }
                    return false;
                }''')
                print(f"通过JavaScript点击'Play now'按钮: {'成功' if result else '失败'}")
                if result:
                    play_now_clicked = True
                
                
                await asyncio.sleep(2)
                
            except Exception as e2:
                print(f"所有尝试均失败: {str(e2)}")
        
        
        continue_clicked = False
        if play_now_clicked:
            print("等待'Continue'按钮出现...")
            
            await asyncio.sleep(3)
            
            
            try:
                print("检查是否出现'MAXIMUM GAMEPLAY REACHED'模态框...")
                
                
                max_gameplay_modal = await page.evaluate('''() => {
                   
                    const textElements = Array.from(document.querySelectorAll('*')).filter(
                        el => {
                            const text = el.textContent || '';
                           
                            return text.toUpperCase().includes('MAXIMUM') && 
                                   text.toUpperCase().includes('GAMEPLAY') && 
                                   text.toUpperCase().includes('REACHED');
                        }
                    );
                    
                    if (textElements.length > 0) {
                        return {found: true, method: 'text'};
                    }
                    
                    
                    const tomorrowElements = Array.from(document.querySelectorAll('*')).filter(
                        el => {
                            const text = el.textContent || '';
                            return text.toUpperCase().includes('PLAY') && 
                                   text.toUpperCase().includes('AGAIN') && 
                                   text.toUpperCase().includes('TOMORROW');
                        }
                    );
                    
                    if (tomorrowElements.length > 0) {
                        return {found: true, method: 'tomorrow'};
                    }
                    
                   
                    
                    const possibleModals = Array.from(document.querySelectorAll('div')).filter(el => {
                        if (!el.children || el.children.length === 0) return false;
                        
                        const style = window.getComputedStyle(el);
                        const position = style.position;
                        const bgColor = style.backgroundColor || '';
                        const opacity = parseFloat(style.opacity || 1);
                        const zIndex = parseInt(style.zIndex || 0);
                        
                      
                        return (position === 'fixed' || position === 'absolute') &&
                               (bgColor.includes('rgba') || bgColor.includes('rgb')) &&
                               opacity < 1 &&
                               zIndex > 10 &&
                               el.offsetWidth > window.innerWidth * 0.5 &&
                               el.offsetHeight > window.innerHeight * 0.5;
                    });
                    
                    if (possibleModals.length > 0) {
                        return {found: true, method: 'visual'};
                    }
                    
                   
                    const closeButtons = Array.from(document.querySelectorAll('*')).filter(el => {
                        const text = el.textContent || '';
                        const style = window.getComputedStyle(el);
                        return (text === 'X' || text === '×' || text === '✕' || text === '✖') &&
                               (style.position === 'absolute' || style.position === 'fixed') &&
                               style.cursor === 'pointer';
                    });
                    
                    if (closeButtons.length > 0) {
                      
                        for (const btn of closeButtons) {
                            const rect = btn.getBoundingClientRect();
                            if (rect.top < window.innerHeight * 0.4 && rect.right > window.innerWidth * 0.6) {
                                return {found: true, method: 'closeBtn'};
                            }
                        }
                    }
                    
                   
                    const totalElements = Array.from(document.querySelectorAll('*')).filter(
                        el => {
                            const text = el.textContent || '';
                            return text.toUpperCase().includes('TOTAL') && 
                                   /\d+/.test(text);
                        }
                    );
                    
                    if (totalElements.length > 0) {
                        return {found: true, method: 'total'};
                    }
                    
                    return {found: false};
                }''')
                
                if max_gameplay_modal.get('found', False):
                    print(f"检测到'MAXIMUM GAMEPLAY REACHED'模态框 (检测方法: {max_gameplay_modal.get('method', 'unknown')})，尝试关闭...")
                    
                    
                    close_button_clicked = await page.evaluate('''() => {
                        
                       
                        const vw = window.innerWidth;
                        const vh = window.innerHeight;
                        
                        
                        const rightTopX = vw * 0.85; 
                        const rightTopY = vh * 0.25; 
                        
                        
                        const element = document.elementFromPoint(rightTopX, rightTopY);
                        
                      
                        if (element) {
                          
                            const text = element.textContent || '';
                            if (text === 'X' || text === '×' || text === '✕' || text === '✖') {
                                element.click();
                                return true;
                            }
                            
                          
                            let clickTarget = element;
                            const maxLevels = 5; 
                            for (let i = 0; i < maxLevels; i++) {
                                if (!clickTarget || clickTarget.tagName === 'BODY') break;
                                
                                const style = window.getComputedStyle(clickTarget);
                                if (clickTarget.tagName === 'BUTTON' || 
                                    clickTarget.tagName === 'A' || 
                                    style.cursor === 'pointer') {
                                    clickTarget.click();
                                    return true;
                                }
                                
                                clickTarget = clickTarget.parentElement;
                            }
                            
                            
                            element.click();
                            return true;
                        }
                        
                       
                        const closeButtons = Array.from(document.querySelectorAll('*')).filter(el => {
                            const text = el.textContent || '';
                            const style = window.getComputedStyle(el);
                            return (text === 'X' || text === '×' || text === '✕' || text === '✖') &&
                                   style.cursor === 'pointer';
                        });
                        
                        if (closeButtons.length > 0) {
                            closeButtons[0].click();
                            return true;
                        }
                        
                       
                        const modalContainer = document.querySelector('div[class*="modal"], div[role="dialog"]');
                        let closeBtn = null;
                        
                        if (modalContainer) {
                         
                            closeBtn = modalContainer.querySelector('button[aria-label="Close"], button[class*="close"]');
                            
                            if (closeBtn) {
                                closeBtn.click();
                                return true;
                            }
                        }
                        
                        return false;
                    }''')
                    
                    if close_button_clicked:
                        print("成功点击模态框关闭按钮")
                    else:
                        print("未找到明确的关闭按钮，尝试点击模态框外区域...")
                        
                        
                        outside_clicked = await page.evaluate('''() => {
                     
                            const vw = window.innerWidth;
                            const vh = window.innerHeight;
                            
                       
                            const clickEvent = new MouseEvent('click', {
                                'view': window,
                                'bubbles': true,
                                'cancelable': true
                            });
                            
                        
                            const points = [
                                {x: 10, y: 10},           
                                {x: vw - 10, y: 10},       
                                {x: 10, y: vh - 10},     
                                {x: vw - 10, y: vh - 10}, 
                                {x: vw / 2, y: 10},        
                                {x: vw / 2, y: vh - 10},  
                                {x: 10, y: vh / 2},       
                                {x: vw - 10, y: vh / 2}   
                            ];
                            
                            let success = false;
                            for (const point of points) {
                                const elem = document.elementFromPoint(point.x, point.y);
                                if (elem) {
                                    elem.dispatchEvent(clickEvent);
                                    success = true;
                                }
                            }
                            
                            return success;
                        }''')
                        
                        if outside_clicked:
                            print("成功点击模态框外区域")
                        else:
                            print("点击模态框外区域失败，尝试按ESC键...")
                            await page.keyboard.press('Escape')
                    
                    
                    await asyncio.sleep(2)
                    
                    
                    modal_gone = await page.evaluate('''() => {
                        
                        const textElements = Array.from(document.querySelectorAll('*')).filter(
                            el => {
                                const text = el.textContent || '';
                                return text.toUpperCase().includes('MAXIMUM') && 
                                       text.toUpperCase().includes('GAMEPLAY') && 
                                       text.toUpperCase().includes('REACHED');
                            }
                        );
                        
                        if (textElements.length > 0) {
                            return false;
                        }
                        
                       
                        const tomorrowElements = Array.from(document.querySelectorAll('*')).filter(
                            el => {
                                const text = el.textContent || '';
                                return text.toUpperCase().includes('PLAY') && 
                                       text.toUpperCase().includes('AGAIN') && 
                                       text.toUpperCase().includes('TOMORROW');
                            }
                        );
                        
                        if (tomorrowElements.length > 0) {
                            return false; 
                        }
                        
                       
                        const totalElements = Array.from(document.querySelectorAll('*')).filter(
                            el => {
                                const text = el.textContent || '';
                                return text.toUpperCase().includes('TOTAL') && 
                                       /\d+/.test(text);
                            }
                        );
                        
                        if (totalElements.length > 0) {
                            return false; 
                        }
                        
                        return true;
                    }''')
                    
                    if modal_gone:
                        print("成功关闭'MAXIMUM GAMEPLAY REACHED'模态框")
                    else:
                        print("模态框仍然存在，尝试其他方法关闭...")
                        
                        try:
                            
                            vw = await page.evaluate('window.innerWidth')
                            vh = await page.evaluate('window.innerHeight')
                            
                            
                            x_button_x = int(vw * 0.85)
                            x_button_y = int(vh * 0.25)
                            
                            
                            await page.mouse.click(x_button_x, x_button_y)
                            print(f"尝试直接点击位置 ({x_button_x}, {x_button_y})")
                            
                            
                            await asyncio.sleep(2)
                        except Exception as e_mouse:
                            print(f"鼠标点击失败: {str(e_mouse)}")
            except Exception as e_modal:
                print(f"处理模态框时出错: {str(e_modal)}")
            
            
            try:
                
                continue_xpath = "//div[contains(text(),'Continue')]"
                continue_button = await page.wait_for_selector(continue_xpath, timeout=5000, state="visible")
                if continue_button:
                    print("找到'Continue'按钮，准备点击...")
                    await continue_button.click()
                    print("已点击'Continue'按钮")
                    continue_clicked = True
                else:
                    raise Exception("未找到Continue按钮")
            except Exception as e3:
                print(f"使用XPath点击Continue按钮失败: {str(e3)}")
                
                
                try:
                    print("尝试通过JavaScript点击'Continue'按钮...")
                    
                    result = await page.evaluate('''() => {
                        const elements = Array.from(document.querySelectorAll('div')).filter(
                            el => el.textContent.includes('Continue')
                        );
                        if (elements.length > 0) {
                            let clickTarget = elements[0];
                         
                            while (clickTarget && clickTarget.tagName !== 'BODY') {
                                if (clickTarget.tagName === 'BUTTON' || clickTarget.tagName === 'A' || 
                                    clickTarget.getAttribute('role') === 'button' || 
                                    clickTarget.style.cursor === 'pointer') {
                                    break;
                                }
                                clickTarget = clickTarget.parentElement;
                            }
                            if (clickTarget) {
                                clickTarget.click();
                                return true;
                            }
                        }
                        return false;
                    }''')
                    print(f"通过JavaScript点击'Continue'按钮: {'成功' if result else '失败'}")
                    if result:
                        continue_clicked = True
                    
                    
                    await asyncio.sleep(2)
                except Exception as e4:
                    print(f"所有Continue按钮点击尝试均失败: {str(e4)}")
        
        
        if continue_clicked:
            print("等待游戏加载...")
            
            await asyncio.sleep(8)  
            
            
            current_url = page.url
            print(f"当前页面URL: {current_url}")
            
            
            try:
                print("检查页面加载状态...")
                
                await page.wait_for_load_state('networkidle', timeout=10000)
                print("页面网络请求已完成")
            except Exception as e_load:
                print(f"等待页面加载完成时出错，但继续执行: {str(e_load)}")
            
            
            page_title = await page.title()
            print(f"页面标题: {page_title}")
            
            
            max_cycles = 3  
            current_cycle = 0
            
            while current_cycle < max_cycles:
                current_cycle += 1
                print(f"开始第 {current_cycle}/{max_cycles} 轮游戏")
                
                
                game_loaded = await page.evaluate('''() => {
                   
                    const gameElements = document.querySelectorAll('.cell, .grid, .board, .game-container');
                    return gameElements.length > 0;
                }''')
                
                if not game_loaded:
                    print("警告: 可能未正确加载游戏页面，尝试重新检查...")
                    
                    await asyncio.sleep(5)
                
                
                try:
                    print("检查inject.js文件...")
                    
                    if not os.path.exists('inject.js'):
                        print("错误: inject.js文件不存在!")
                        break
                    
                    print("读取注入脚本...")
                    try:
                        with open('inject.js', 'r', encoding='utf-8') as f:
                            inject_script = f.read()
                        print(f"注入脚本读取成功，大小: {len(inject_script)} 字节")
                    except Exception as e_read:
                        print(f"读取inject.js文件失败: {str(e_read)}")
                        break
                    
                    print("注入扫雷自动解决脚本...")
                    try:
                        
                        pre_inject_check = await page.evaluate('''() => {
                            return {
                                url: window.location.href,
                                title: document.title,
                                elements: document.body.innerHTML.length,
                                readyState: document.readyState
                            };
                        }''')
                        print(f"注入前页面状态: {pre_inject_check}")
                        
                        
                        await page.evaluate(inject_script)
                        print("脚本注入成功！自动扫雷开始运行")
                        
                        
                        post_inject_check = await page.evaluate('''() => {
                        
                            return {
                                scriptRunning: window.autoMinesweeperRunning === true || false,
                                minesweeperHelper: typeof window.minesweeperHelper !== 'undefined',
                                errors: window.lastInjectionError || 'none'
                            };
                        }''')
                        print(f"注入后状态: {post_inject_check}")
                        
                    except Exception as e_inject:
                        print(f"执行脚本注入失败: {str(e_inject)}")
                        print("尝试简化版注入...")
                        
                        
                        try:
                            await page.add_script_tag(content=inject_script)
                            print("通过script标签注入成功")
                        except Exception as e_simple_inject:
                            print(f"简化注入也失败: {str(e_simple_inject)}")
                            break
                    
                    
                    print("让脚本运行33秒...")
                    
                    for i in range(6):
                        await asyncio.sleep(5)
                        print(f"脚本运行中... {(i+1)*5}/33 秒")
                        
                        
                        try:
                            game_progress = await page.evaluate('''() => {
                         
                                const openedCells = document.querySelectorAll('.cell.open, .revealed, .flagged').length;
                                return {
                                    openedCells: openedCells,
                                    time: new Date().toISOString()
                                };
                            }''')
                            print(f"游戏进度: {game_progress}")
                        except Exception as e_progress:
                            print(f"检查游戏进度失败: {str(e_progress)}")
                    
                    await asyncio.sleep(3)  
                    
                    
                    print("检查'Play Again'按钮...")
                    play_again_clicked = False
                    
                    try:
                        
                        play_again_xpath = "//div[normalize-space()='Play Again']"
                        play_again_button = await page.wait_for_selector(play_again_xpath, timeout=5000, state="visible")
                        if play_again_button:
                            print("找到'Play Again'按钮，准备点击...")
                            await play_again_button.click()
                            print("已点击'Play Again'按钮")
                            play_again_clicked = True
                            
                            
                            await asyncio.sleep(3)
                        else:
                            print("未找到'Play Again'按钮，尝试JavaScript方法")
                            raise Exception("未找到Play Again按钮")
                    except Exception as e_play_again:
                        print(f"使用XPath点击Play Again按钮失败: {str(e_play_again)}")
                        
                        
                        try:
                            print("尝试通过JavaScript点击'Play Again'按钮...")
                            
                            result = await page.evaluate('''() => {
                                const elements = Array.from(document.querySelectorAll('div')).filter(
                                    el => el.textContent.trim() === 'Play Again'
                                );
                                if (elements.length > 0) {
                                    let clickTarget = elements[0];
                                   
                                    while (clickTarget && clickTarget.tagName !== 'BODY') {
                                        if (clickTarget.tagName === 'BUTTON' || clickTarget.tagName === 'A' || 
                                            clickTarget.getAttribute('role') === 'button' || 
                                            clickTarget.style.cursor === 'pointer') {
                                            break;
                                        }
                                        clickTarget = clickTarget.parentElement;
                                    }
                                    if (clickTarget) {
                                        clickTarget.click();
                                        return true;
                                    }
                                }
                                return false;
                            }''')
                            print(f"通过JavaScript点击'Play Again'按钮: {'成功' if result else '失败'}")
                            
                            if result:
                                play_again_clicked = True
                                
                                await asyncio.sleep(3)
                            else:
                                print("无法找到或点击'Play Again'按钮，跳出循环")
                                break
                                
                        except Exception as e_js:
                            print(f"所有点击'Play Again'尝试均失败: {str(e_js)}")
                            print("结束游戏循环")
                            break
                        
                    if not play_again_clicked:
                        print("无法找到或点击'Play Again'按钮，跳出循环")
                        break
                    
                except Exception as e5:
                    print(f"注入脚本失败: {str(e5)}")
                    break
            
            print(f"完成了 {current_cycle} 轮游戏")
            
            
            print("游戏循环结束，开始点击返回并领取奖励...")
            
            
            try:
                print("尝试点击屏幕区域关闭结果对话框...")
                
                
                result = await page.evaluate('''() => {
                  
                    const vw = window.innerWidth;
                    const vh = window.innerHeight;
                    
                   
                    const clickEvent = new MouseEvent('click', {
                        'view': window,
                        'bubbles': true,
                        'cancelable': true
                    });
                    
                   
                    let success = false;
                    
                
                    let elem = document.elementFromPoint(vw/2, vh*0.1);
                    if (elem) {
                        elem.dispatchEvent(clickEvent);
                        success = true;
                    }
                    
               
                    elem = document.elementFromPoint(vw*0.1, vh/2);
                    if (elem) {
                        elem.dispatchEvent(clickEvent);
                        success = true;
                    }
                    
                 
                    elem = document.elementFromPoint(vw*0.9, vh/2);
                    if (elem) {
                        elem.dispatchEvent(clickEvent);
                        success = true;
                    }
                    
                
                    elem = document.elementFromPoint(vw/2, vh*0.9);
                    if (elem) {
                        elem.dispatchEvent(clickEvent);
                        success = true;
                    }
                    
                    return success;
                }''')
                
                print(f"尝试点击屏幕区域关闭对话框: {'成功' if result else '失败'}")
                
                
                await asyncio.sleep(2)
                
                
                if not result:
                    print("尝试按ESC键关闭对话框...")
                    await page.keyboard.press('Escape')
                    await asyncio.sleep(1)
                
                
                print("等待页面恢复...")
                await asyncio.sleep(3)

                
                print("检查页面上的'Return Home'按钮...")
                return_home_clicked = False
                try:
                    
                    return_home_xpath = "//div[@class='fPSBzf bYPztT bYPznK pezuA cMGtQw pBppg dMMuNs']//button[@type='button']"
                    
                    simple_return_home_xpath = "//button[contains(., 'Return Home')]"
                    
                    
                    return_home_button = await page.wait_for_selector(return_home_xpath, timeout=5000, state="visible")
                    if return_home_button:
                        print("找到'Return Home'按钮，准备点击...")
                        await return_home_button.click()
                        print("已点击'Return Home'按钮")
                        return_home_clicked = True
                    else:
                        
                        return_home_button = await page.wait_for_selector(simple_return_home_xpath, timeout=5000, state="visible")
                        if return_home_button:
                            print("找到简化的'Return Home'按钮，准备点击...")
                            await return_home_button.click()
                            print("已点击'Return Home'按钮")
                            return_home_clicked = True
                        else:
                            raise Exception("未找到Return Home按钮")
                except Exception as e_return_home:
                    print(f"使用XPath点击Return Home按钮失败: {str(e_return_home)}")
                    
                    
                    try:
                        print("尝试通过JavaScript点击'Return Home'按钮...")
                        result = await page.evaluate('''() => {
                        
                            const buttons = Array.from(document.querySelectorAll('button')).filter(
                                el => el.textContent.includes('Return Home')
                            );
                            if (buttons.length > 0) {
                                buttons[0].click();
                                return true;
                            }
                            
                         
                            const allButtons = document.querySelectorAll('button');
                            if (allButtons.length > 0) {
                           
                                const viewportHeight = window.innerHeight;
                                const viewportWidth = window.innerWidth;
                                const centerX = viewportWidth / 2;
                                const centerY = viewportHeight / 2;
                                
                            
                                let closestButton = null;
                                let closestDistance = Infinity;
                                
                                for (const button of allButtons) {
                                    const rect = button.getBoundingClientRect();
                                    const buttonCenterX = rect.left + rect.width / 2;
                                    const buttonCenterY = rect.top + rect.height / 2;
                                    
                                    const distance = Math.sqrt(
                                        Math.pow(buttonCenterX - centerX, 2) + 
                                        Math.pow(buttonCenterY - centerY, 2)
                                    );
                                    
                                    if (distance < closestDistance) {
                                        closestDistance = distance;
                                        closestButton = button;
                                    }
                                }
                                
                                if (closestButton) {
                                    closestButton.click();
                                    return true;
                                }
                            }
                            
                            return false;
                        }''')
                        print(f"通过JavaScript点击'Return Home'按钮: {'成功' if result else '失败'}")
                        if result:
                            return_home_clicked = True
                    except Exception as e_return_home_js:
                        print(f"通过JavaScript点击Return Home按钮失败: {str(e_return_home_js)}")

                
                await asyncio.sleep(3)
                
                
                print("尝试点击'Roll Now'按钮...")
                roll_now_clicked = False
                roll_xpath = "//p[normalize-space()='Roll now']"
                try:
                    roll_button = await page.wait_for_selector(roll_xpath, timeout=5000, state="visible")
                    if roll_button:
                        print("找到'Roll Now'按钮，准备点击...")
                        await roll_button.click()
                        print("已点击'Roll Now'按钮")
                        roll_now_clicked = True
                    else:
                        raise Exception("未找到Roll Now按钮")
                except Exception as e_roll:
                    print(f"使用XPath点击Roll Now按钮失败: {str(e_roll)}")
                    
                    
                    try:
                        print("尝试通过JavaScript点击'Roll Now'按钮...")
                        result = await page.evaluate('''() => {
                            const elements = Array.from(document.querySelectorAll('p')).filter(
                                el => el.textContent.trim() === 'Roll now'
                            );
                            if (elements.length > 0) {
                                let clickTarget = elements[0];
                             
                                while (clickTarget && clickTarget.tagName !== 'BODY') {
                                    if (clickTarget.tagName === 'BUTTON' || clickTarget.tagName === 'A' || 
                                        clickTarget.getAttribute('role') === 'button' || 
                                        clickTarget.style.cursor === 'pointer') {
                                        break;
                                    }
                                    clickTarget = clickTarget.parentElement;
                                }
                                if (clickTarget) {
                                    clickTarget.click();
                                    return true;
                                }
                            }
                            return false;
                        }''')
                        print(f"通过JavaScript点击'Roll Now'按钮: {'成功' if result else '失败'}")
                        roll_now_clicked = result
                    except Exception as e_roll_js:
                        print(f"JavaScript点击Roll Now按钮失败: {str(e_roll_js)}")
                
                
                if roll_now_clicked:
                    
                    await asyncio.sleep(3)
                    
                    
                    print("尝试点击'Let's roll'按钮...")
                    
                    absolute_lets_roll_xpath = "/html[1]/body[1]/div[1]/div[11]/div[3]/div[1]/div[1]/div[3]/button[1]"
                    lets_roll_clicked = False
                    try:
                        
                        lets_roll_button = await page.wait_for_selector(absolute_lets_roll_xpath, timeout=5000, state="visible")
                        if lets_roll_button:
                            print("找到绝对路径的'Let's roll'按钮，准备点击...")
                            await lets_roll_button.click()
                            print("已点击'Let's roll'按钮")
                            lets_roll_clicked = True
                        else:
                            
                            simplified_lets_roll_xpath = "//button[contains(@class, 'hoEiop')]"
                            lets_roll_button = await page.wait_for_selector(simplified_lets_roll_xpath, timeout=5000, state="visible")
                            if lets_roll_button:
                                print("找到简化的'Let's roll'按钮，准备点击...")
                                await lets_roll_button.click()
                                print("已点击'Let's roll'按钮")
                                lets_roll_clicked = True
                            else:
                                
                                lets_roll_xpath = "//button[@class='hoEiop dgDkEX iFUqYl bZRhvx eAZrqn diIxfU jTWvec ThTOq efvJEH cGFOJB fzoqjJ coifUy eAZrpM kyvghW fznPAm fzoAXm eePqkU']"
                                lets_roll_button = await page.wait_for_selector(lets_roll_xpath, timeout=5000, state="visible")
                                if lets_roll_button:
                                    print("找到'Let's roll'按钮，准备点击...")
                                    await lets_roll_button.click()
                                    print("已点击'Let's roll'按钮")
                                    lets_roll_clicked = True
                                else:
                                    raise Exception("未找到Let's roll按钮")
                    except Exception as e_lets_roll:
                        print(f"使用XPath点击Let's roll按钮失败: {str(e_lets_roll)}")
                        
                        
                        try:
                            print("尝试通过JavaScript点击'Let's roll'按钮...")
                            result = await page.evaluate('''() => {
                       
                                const xpathResult = document.evaluate(
                                    "/html[1]/body[1]/div[1]/div[11]/div[3]/div[1]/div[1]/div[3]/button[1]", 
                                    document, 
                                    null, 
                                    XPathResult.FIRST_ORDERED_NODE_TYPE, 
                                    null
                                );
                                
                                if (xpathResult && xpathResult.singleNodeValue) {
                                    xpathResult.singleNodeValue.click();
                                    return true;
                                }
                                
                                
                                const elements = Array.from(document.querySelectorAll('button')).filter(
                                    el => el.textContent.includes("Let's roll") || el.textContent.includes("Let's Roll")
                                );
                                
                                if (elements.length > 0) {
                                    elements[0].click();
                                    return true;
                                }
                                
                              
                                const classButton = document.querySelector('button[class*="hoEiop"]');
                                if (classButton) {
                                    classButton.click();
                                    return true;
                                }
                                
                                return false;
                            }''')
                            print(f"通过JavaScript点击'Let's roll'按钮: {'成功' if result else '失败'}")
                            if result:
                                lets_roll_clicked = True
                        except Exception as e_lets_roll_js:
                            print(f"所有'Let's roll'点击尝试均失败: {str(e_lets_roll_js)}")

                    
                    if lets_roll_clicked:
                        
                        print("等待'Throw Dice'按钮出现...")
                        await asyncio.sleep(3)
                        
                        
                        print("尝试点击'Throw Dice'按钮...")
                        throw_dice_xpath = "//p[normalize-space()='Throw Dice']"
                        throw_dice_clicked = False
                        try:
                            throw_dice_button = await page.wait_for_selector(throw_dice_xpath, timeout=5000, state="visible")
                            if throw_dice_button:
                                print("找到'Throw Dice'按钮，准备点击...")
                                await throw_dice_button.click()
                                print("已点击'Throw Dice'按钮")
                                throw_dice_clicked = True
                            else:
                                raise Exception("未找到Throw Dice按钮")
                        except Exception as e_throw_dice:
                            print(f"使用XPath点击Throw Dice按钮失败: {str(e_throw_dice)}")
                            
                            
                            try:
                                print("尝试通过JavaScript点击'Throw Dice'按钮...")
                                result = await page.evaluate('''() => {
                                  
                                    const elements = Array.from(document.querySelectorAll('p')).filter(
                                        el => el.textContent.trim() === 'Throw Dice'
                                    );
                                    
                                    if (elements.length > 0) {
                                        let clickTarget = elements[0];
                                     
                                        while (clickTarget && clickTarget.tagName !== 'BODY') {
                                            if (clickTarget.tagName === 'BUTTON' || clickTarget.tagName === 'A' || 
                                                clickTarget.getAttribute('role') === 'button' || 
                                                clickTarget.style.cursor === 'pointer') {
                                                break;
                                            }
                                            clickTarget = clickTarget.parentElement;
                                        }
                                        if (clickTarget) {
                                            clickTarget.click();
                                            return true;
                                        }
                                    }
                                    
                                   
                                    const allElements = Array.from(document.querySelectorAll('*'));
                                    const throwDiceElements = allElements.filter(
                                        el => el.textContent && el.textContent.includes('Throw Dice')
                                    );
                                    
                                    if (throwDiceElements.length > 0) {
                                        let clickTarget = throwDiceElements[0];
                                   
                                        while (clickTarget && clickTarget.tagName !== 'BODY') {
                                            if (clickTarget.tagName === 'BUTTON' || clickTarget.tagName === 'A' || 
                                                clickTarget.getAttribute('role') === 'button' || 
                                                clickTarget.style.cursor === 'pointer') {
                                                break;
                                            }
                                            clickTarget = clickTarget.parentElement;
                                        }
                                        if (clickTarget) {
                                            clickTarget.click();
                                            return true;
                                        }
                                    }
                                    
                                    return false;
                                }''')
                                print(f"通过JavaScript点击'Throw Dice'按钮: {'成功' if result else '失败'}")
                                throw_dice_clicked = result
                            except Exception as e_throw_dice_js:
                                print(f"所有'Throw Dice'点击尝试均失败: {str(e_throw_dice_js)}")
                        
                        
                        if throw_dice_clicked:
                            print("等待骰子动画和结果显示...")
                            await asyncio.sleep(5)
                            print("骰子动画完成，结果已显示")
                    else:
                        print("未能成功点击'Let's roll'按钮，跳过'Throw Dice'步骤")

                
                await asyncio.sleep(3)
                print("完成全部操作流程！")
                
            except Exception as e_all:
                print(f"执行点击系列按钮过程中出错: {str(e_all)}")
                print("操作未能完全完成")
    
    except Exception as e:
        print(f"操作过程中出错: {str(e)}")
    
    print('浏览器操作完成')


if __name__ == '__main__':
    asyncio.run(main())
