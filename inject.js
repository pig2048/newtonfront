
(function() {
    
    const DELAY_BETWEEN_MOVES = 1000; 
    
    
    let gameState = {
        tiles: [], 
        rows: 10,  
        cols: 10,  
        gameOver: false,
        clickedCells: new Set(), 
        runningLoop: true 
    };
    
    
    window.stopMinesweeper = function() {
        console.log('正在停止扫雷脚本...');
        gameState.runningLoop = false;
        console.log('扫雷脚本已停止!');
    };
    
    
    function parseGameState() {
        
        
        const gameRow = document.querySelector('.gamerow');
        if (!gameRow) {
            console.error('找不到游戏棋盘，请确保您在扫雷游戏页面上运行此脚本');
            return null;
        }
        
        
        const gameCols = gameRow.querySelectorAll('.gamecol');
        if (!gameCols || gameCols.length === 0) {
            console.error('找不到游戏棋盘行，请确保您在扫雷游戏页面上运行此脚本');
            return null;
        }
        
        
        gameState.rows = gameCols.length;
        gameState.cols = gameCols[0].children.length;
        
        
        gameState.tiles = [];
        for (let y = 0; y < gameState.rows; y++) {
            gameState.tiles[y] = [];
            for (let x = 0; x < gameState.cols; x++) {
                gameState.tiles[y][x] = null;
            }
        }
        
        
        for (let y = 0; y < gameState.rows; y++) {
            const row = gameCols[y]; 
            const cells = row.children; 
            
            for (let x = 0; x < cells.length; x++) {
                const cell = cells[x];
                const tile = cell.querySelector('.tile');
                
                if (!tile) continue;
                
                
                
                
                const isNumberTile = tile.classList.contains('tile-changed') && 
                                    tile.textContent && !isNaN(parseInt(tile.textContent));
                
                
                const isEmptyTile = tile.style.backgroundColor === 'transparent' && 
                                  tile.style.color === 'white';
                
                
                const isUnclickedTile = !tile.classList.contains('tile-changed') && 
                                     !tile.classList.contains('tile-flagged') && 
                                     !tile.classList.contains('tile-mine') && 
                                     !tile.classList.contains('bomb') && 
                                     !isEmptyTile && 
                                     (!tile.textContent || tile.textContent.trim() === '');
                
                
                const isUnflaggedBomb = tile.classList.contains('bomb') && 
                                      tile.classList.contains('bomb-unflagged-won');
                
                
                const isExplodedBomb = tile.classList.contains('bomb') && 
                                     !tile.classList.contains('bomb-unflagged-won');
                
                if (isUnflaggedBomb) {
                    
                    gameState.tiles[y][x] = 'B';
                    gameState.gameOver = true; 
                    console.log('游戏胜利！检测到未标记的雷');
                } else if (isExplodedBomb) {
                    
                    gameState.tiles[y][x] = 'X';
                    gameState.gameOver = true; 
                    console.log('游戏失败！踩到地雷了');
                } else if (tile.classList.contains('tile-flagged')) {
                    
                    gameState.tiles[y][x] = 'F';
                } else if (tile.classList.contains('tile-mine')) {
                    
                    gameState.tiles[y][x] = 'M';
                    gameState.gameOver = true;
                } else if (isNumberTile) {
                    
                    gameState.tiles[y][x] = parseInt(tile.textContent);
                } else if (isEmptyTile) {
                    
                    gameState.tiles[y][x] = 0;
                } else if (isUnclickedTile) {
                    
                    gameState.tiles[y][x] = null;
                } else {
                    
                    console.log(`无法识别的格子类型 at (${x}, ${y})`, tile);
                    gameState.tiles[y][x] = null;
                }
            }
        }
        
        
        return gameState;
    }
    
    
    function clickTile(x, y) {
        
        const cellKey = `${x},${y}`;
        if (gameState.clickedCells.has(cellKey)) {
            console.warn(`格子 (${x}, ${y}) 已经被点击过，跳过`);
            return false;
        }
        
        
        const gameRow = document.querySelector('.gamerow');
        if (!gameRow) {
            console.error('找不到游戏棋盘');
            return false;
        }
        
        
        const gameCols = gameRow.querySelectorAll('.gamecol');
        if (!gameCols || gameCols.length <= y) {
            console.error(`找不到行 ${y}`);
            return false;
        }
        
        
        const cells = gameCols[y].children;
        if (!cells || cells.length <= x) {
            console.error(`找不到列 ${x}`);
            return false;
        }
        
        
        const tile = cells[x].querySelector('.tile');
        if (!tile) {
            console.error(`找不到格子 (${x}, ${y})`);
            return false;
        }
        
        
        
        
        const isNumberTile = tile.classList.contains('tile-changed') && 
                            tile.textContent && !isNaN(parseInt(tile.textContent));
        
        
        const isEmptyTile = tile.style.backgroundColor === 'transparent' && 
                          tile.style.color === 'white';
        
        
        if (isNumberTile || isEmptyTile || tile.classList.contains('tile-flagged')) {
            console.warn(`格子 (${x}, ${y}) 已经被翻开或标记，跳过`);
            return false;
        }
        
        console.log(`点击格子 (${x}, ${y})`);
        
        
        gameState.clickedCells.add(cellKey);
        
        
        const clickEvent = new MouseEvent('click', {
            bubbles: true,
            cancelable: true,
            view: window
        });
        
        tile.dispatchEvent(clickEvent);
        return true;
    }
    
    
    function calculateNextMove() {
        const { tiles, rows, cols } = gameState;
        
        
        let revealed = [];  
        let unrevealed = [];  
        
        for (let y = 0; y < rows; y++) {
            for (let x = 0; x < cols; x++) {
                if (tiles[y][x] !== null && tiles[y][x] !== 'F') {
                    if (typeof tiles[y][x] === 'number') {
                        revealed.push([x, y, tiles[y][x]]);
                    }
                } else if (tiles[y][x] === null) {
                    unrevealed.push([x, y]);
                }
            }
        }
        
        
        if (revealed.length === 0) {
            const corners = [[0, 0], [0, rows-1], [cols-1, 0], [cols-1, rows-1]];
            return corners[Math.floor(Math.random() * corners.length)];
        }
        
        
        let safeCells = new Set();  
        let mineCells = new Set();  
        
        
        let neighborsMap = {};
        for (let y = 0; y < rows; y++) {
            for (let x = 0; x < cols; x++) {
                const key = `${x},${y}`;
                neighborsMap[key] = [];
                for (let dx = -1; dx <= 1; dx++) {
                    for (let dy = -1; dy <= 1; dy++) {
                        if (dx === 0 && dy === 0) continue;
                        const nx = x + dx;
                        const ny = y + dy;
                        if (nx >= 0 && nx < cols && ny >= 0 && ny < rows) {
                            neighborsMap[key].push([nx, ny]);
                        }
                    }
                }
            }
        }
        
        
        for (const [x, y, value] of revealed) {
            if (value === 0) {
                
                const key = `${x},${y}`;
                for (const [nx, ny] of neighborsMap[key]) {
                    if (tiles[ny][nx] === null) {
                        safeCells.add(`${nx},${ny}`);
                    }
                }
            } else {
                
                const key = `${x},${y}`;
                const unknownNeighbors = neighborsMap[key].filter(([nx, ny]) => tiles[ny][nx] === null);
                const flaggedNeighbors = neighborsMap[key].filter(([nx, ny]) => tiles[ny][nx] === 'F');
                
                if (unknownNeighbors.length + flaggedNeighbors.length === value) {
                    
                    for (const [nx, ny] of unknownNeighbors) {
                        mineCells.add(`${nx},${ny}`);
                    }
                }
            }
        }
        
        
        for (const [x, y, value] of revealed) {
            if (value > 0) {
                const key = `${x},${y}`;
                
                const knownMines = neighborsMap[key].filter(([nx, ny]) => 
                    tiles[ny][nx] === 'F' || mineCells.has(`${nx},${ny}`)
                ).length;
                
                const unknownNeighbors = neighborsMap[key].filter(([nx, ny]) => 
                    tiles[ny][nx] === null && !mineCells.has(`${nx},${ny}`)
                );
                
                
                if (knownMines === value && unknownNeighbors.length > 0) {
                    for (const [nx, ny] of unknownNeighbors) {
                        safeCells.add(`${nx},${ny}`);
                    }
                }
            }
        }
        
        
        if (safeCells.size > 0) {
            
            let bestSafeCell = null;
            let maxRevealedNeighbors = -1;
            
            for (const cellKey of safeCells) {
                const [x, y] = cellKey.split(',').map(Number);
                const key = `${x},${y}`;
                const revealedNeighbors = neighborsMap[key].filter(([nx, ny]) => 
                    typeof tiles[ny][nx] === 'number'
                ).length;
                
                if (revealedNeighbors > maxRevealedNeighbors) {
                    maxRevealedNeighbors = revealedNeighbors;
                    bestSafeCell = [x, y];
                }
            }
            
            if (bestSafeCell) {
                console.log('找到安全格子:', bestSafeCell);
                return bestSafeCell;
            }
            
            
            const safeCellsArray = Array.from(safeCells).map(key => key.split(',').map(Number));
            const randomSafeCell = safeCellsArray[Math.floor(Math.random() * safeCellsArray.length)];
            console.log('随机安全格子:', randomSafeCell);
            return randomSafeCell;
        }
        
        
        
        let probabilityMap = {};
        for (const [x, y] of unrevealed) {
            if (!mineCells.has(`${x},${y}`)) {
                probabilityMap[`${x},${y}`] = 0.0;
            }
        }
        
        
        for (const [x, y, value] of revealed) {
            if (value > 0) {
                const key = `${x},${y}`;
                const unknownNeighbors = neighborsMap[key].filter(([nx, ny]) => 
                    tiles[ny][nx] === null && !mineCells.has(`${nx},${ny}`)
                );
                
                if (unknownNeighbors.length > 0) {
                    
                    const knownMines = neighborsMap[key].filter(([nx, ny]) => 
                        tiles[ny][nx] === 'F' || mineCells.has(`${nx},${ny}`)
                    ).length;
                    
                    
                    const remainingMines = value - knownMines;
                    
                    
                    if (remainingMines > 0) {
                        const mineProb = remainingMines / unknownNeighbors.length;
                        for (const [nx, ny] of unknownNeighbors) {
                            const cellKey = `${nx},${ny}`;
                            if (cellKey in probabilityMap) {
                                
                                probabilityMap[cellKey] = Math.max(probabilityMap[cellKey], mineProb);
                            }
                        }
                    }
                }
            }
        }
        
        
        
        let edgeScores = {};
        for (const cellKey in probabilityMap) {
            const [x, y] = cellKey.split(',').map(Number);
            const key = `${x},${y}`;
            
            const knownNeighbors = neighborsMap[key].filter(([nx, ny]) => 
                typeof tiles[ny][nx] === 'number'
            ).length;
            edgeScores[cellKey] = knownNeighbors;
        }
        
        
        let bestCell = null;
        let minProbability = Infinity;
        let maxEdgeScore = -1;
        
        for (const cellKey in probabilityMap) {
            const prob = probabilityMap[cellKey];
            if (prob < minProbability || (prob === minProbability && edgeScores[cellKey] > maxEdgeScore)) {
                minProbability = prob;
                maxEdgeScore = prob === minProbability ? edgeScores[cellKey] : edgeScores[cellKey];
                bestCell = cellKey.split(',').map(Number);
            }
        }
        
        
        if (bestCell) {
            console.log(`基于概率的最佳格子: (${bestCell[0]}, ${bestCell[1]}) (概率: ${minProbability}, 边缘分: ${maxEdgeScore})`);
            return bestCell;
        }
        
        
        
        const safeUnknown = unrevealed.filter(([x, y]) => !mineCells.has(`${x},${y}`));
        if (safeUnknown.length > 0) {
            const randomCell = safeUnknown[Math.floor(Math.random() * safeUnknown.length)];
            console.log(`随机格子 (后备): (${randomCell[0]}, ${randomCell[1]})`);
            return randomCell;
        }
        
        
        if (unrevealed.length > 0) {
            const lastResort = unrevealed[Math.floor(Math.random() * unrevealed.length)];
            console.log(`最后手段: (${lastResort[0]}, ${lastResort[1]})`);
            return lastResort;
        }
        
        
        let anyUnclickedCell = null;
        
        
        for (let y = 0; y < rows; y++) {
            for (let x = 0; x < cols; x++) {
                if (tiles[y][x] === null && !gameState.clickedCells.has(`${x},${y}`)) {
                    anyUnclickedCell = [x, y];
                    console.log(`找到未点击的格子: (${x}, ${y})`);
                    return anyUnclickedCell;
                }
            }
        }
        
        
        console.log('所有格子都已点击过或被标记，游戏可能已完成');
        gameState.runningLoop = false;
        return null; 
    }
    
    
    function gameLoop() {
        
        if (!gameState.runningLoop) {
            console.log('游戏循环已停止');
            return;
        }
        
        
        if (!parseGameState()) {
            console.error('无法解析游戏状态，5秒后重试...');
            if (gameState.runningLoop) {
                setTimeout(gameLoop, 5000);
            }
            return;
        }
        
        
        if (gameState.gameOver) {
            console.log('游戏结束!');
            return;
        }
        
        
        const nextMove = calculateNextMove();
        
        
        if (!nextMove) {
            console.log('没有可用的下一步，停止游戏循环');
            return;
        }
        
        const [nextX, nextY] = nextMove;
        
        
        if (clickTile(nextX, nextY)) {
            
            if (gameState.runningLoop) {
                setTimeout(gameLoop, DELAY_BETWEEN_MOVES);
            }
        } else {
            console.error('点击失败，3秒后重试...');
            
            gameState.clickedCells.add(`${nextX},${nextY}`);
            if (gameState.runningLoop) {
                setTimeout(gameLoop, 3000);
            }
        }
    }
    
    
    console.log('扫雷自动化脚本已启动!');
    console.log('要停止脚本，请在控制台输入 stopMinesweeper() 并回车');
    setTimeout(gameLoop, 1000); 
})();