# Implementation Plan

[Overview]
将贝叶斯优化中的串行action生成改为并行执行，每个action最多重试5次，确保跨平台兼容性并保持进程同步。

本项目旨在优化BOTree-AHD系统中的启发式生成延迟问题。当前系统在`source/bo_local.py`的`expand()`方法中串行执行6种action类型（i1, e1, e2, m1, m2, s1），每个action都需要调用LLM API生成代码，导致显著的等待时间。优化方案将使用Python的`concurrent.futures.ThreadPoolExecutor`实现并行生成，每个action独立执行最多5次重试，所有进程在评估前同步完成feature vector生成。该方案需要保持跨平台兼容性（macOS/Linux/Windows），确保向后兼容现有接口，并通过适当的同步机制保证数据一致性。

[Types]  
添加并行执行相关的类型定义和数据结构。

新增类型定义：
1. `ActionTask`: 表示单个action生成任务的命名元组
   - `action`: str - action类型名称
   - `parent_node`: HeuristicNode - 父节点引用
   - `max_retries`: int - 最大重试次数（默认5）

2. `GenerationResult`: 表示action生成结果的命名元组
   - `success`: bool - 是否成功生成
   - `action`: str - action类型
   - `code`: Optional[str] - 生成的代码（成功时为字符串，失败时为None）
   - `algorithm`: Optional[str] - 算法描述（成功时为字符串，失败时为None）
   - `feature_vector`: Optional[np.ndarray] - 特征向量（成功时为数组，失败时为None）
   - `error`: Optional[str] - 错误信息（失败时）

3. `ParallelConfig`: 并行执行配置类
   - `max_workers`: int - 最大工作线程数（默认6，对应6种action类型）
   - `timeout_per_action`: int - 每个action的超时时间（秒）
   - `max_retries`: int - 最大重试次数（默认5）

现有类型修改：
1. `HeuristicNode`类：添加`generation_status`字段跟踪生成状态
2. `BayesianOptimizer_Local`类：添加`parallel_config`属性和相关并行方法

[Files]
修改现有文件以支持并行action生成，添加辅助函数。

详细文件修改：
1. **新文件**：`source/parallel_executor.py`
   - 路径：`/Users/chriswu/Github/BOTree-AHD-Code/source/parallel_executor.py`
   - 目的：封装并行执行逻辑，提供线程安全的action生成
   - 内容：包含`ParallelActionExecutor`类，管理线程池和任务分发

2. **修改文件**：`source/bo_local.py`
   - 路径：`/Users/chriswu/Github/BOTree-AHD-Code/source/bo_local.py`
   - 修改`expand()`方法：将串行循环改为并行执行
   - 添加`_generate_single_action()`方法：封装单个action的生成逻辑
   - 添加`_process_generation_results()`方法：处理并行生成结果
   - 添加`parallel_config`属性：配置并行执行参数
   - 修改`__init__()`方法：初始化并行配置

3. **修改文件**：`source/bo_interface.py`
   - 路径：`/Users/chriswu/Github/BOTree-AHD-Code/source/bo_interface.py`
   - 修改`generate_heuristic_by_action()`方法：添加重试逻辑
   - 添加`_generate_with_retry()`方法：实现最多5次重试

4. **修改文件**：`requirements.txt`
   - 路径：`/Users/chriswu/Github/BOTree-AHD-Code/requirements.txt`
   - 确保已包含必要的并发库（Python标准库已包含concurrent.futures）

5. **新文件**：`tests/test_parallel_expand.py`
   - 路径：`/Users/chriswu/Github/BOTree-AHD-Code/tests/test_parallel_expand.py`
   - 目的：测试并行扩展功能的正确性和性能

[Functions]
修改和添加函数以支持并行执行和重试机制。

详细函数修改：
1. **新函数**：`ParallelActionExecutor.execute_actions()`（在parallel_executor.py中）
   - 签名：`def execute_actions(self, actions: List[str], parent_node: HeuristicNode, max_retries: int = 5) -> List[GenerationResult]`
   - 目的：并行执行多个action生成任务
   - 返回：所有action的生成结果列表

2. **新函数**：`ParallelActionExecutor._execute_single_action()`（在parallel_executor.py中）
   - 签名：`def _execute_single_action(self, action: str, parent_node: HeuristicNode, max_retries: int) -> GenerationResult`
   - 目的：执行单个action的生成，包含重试逻辑

3. **修改函数**：`BayesianOptimizer_Local.expand()`（在bo_local.py中）
   - 当前签名：`def expand(self, node: HeuristicNode) -> List[HeuristicNode]`
   - 修改内容：将串行循环改为调用`ParallelActionExecutor`
   - 保持返回类型不变：返回生成的子节点列表

4. **新函数**：`BayesianOptimizer_Local._generate_single_action()`（在bo_local.py中）
   - 签名：`def _generate_single_action(self, action: str, parent_node: HeuristicNode, max_retries: int = 5) -> Optional[HeuristicNode]`
   - 目的：封装单个action的生成、去重检查和特征向量计算

5. **新函数**：`BayesianOptimizer_Local._process_generation_results()`（在bo_local.py中）
   - 签名：`def _process_generation_results(self, results: List[GenerationResult], parent_node: HeuristicNode) -> List[HeuristicNode]`
   - 目的：将并行生成结果转换为HeuristicNode对象

6. **修改函数**：`BOInterface.generate_heuristic_by_action()`（在bo_interface.py中）
   - 当前签名：`def generate_heuristic_by_action(self, action: str) -> Tuple[str, str]`
   - 修改内容：添加重试逻辑，最多尝试5次
   - 添加内部函数：`_generate_with_retry()`

7. **新函数**：`BOInterface._generate_with_retry()`（在bo_interface.py中）
   - 签名：`def _generate_with_retry(self, action: str, max_retries: int = 5) -> Tuple[str, str]`
   - 目的：实现带重试的action生成，处理超时和API错误

[Classes]
创建新的并行执行器类，修改现有优化器类。

详细类修改：
1. **新类**：`ParallelActionExecutor`（在parallel_executor.py中）
   - 文件路径：`source/parallel_executor.py`
   - 关键方法：
     - `__init__(self, bo_interface, max_workers: int = 6)`
     - `execute_actions(actions, parent_node, max_retries)`
     - `_execute_single_action(action, parent_node, max_retries)`
     - `shutdown()`
   - 继承：不继承，独立类
   - 线程安全：使用线程锁保护共享资源

2. **修改类**：`BayesianOptimizer_Local`（在bo_local.py中）
   - 添加属性：
     - `parallel_executor: Optional[ParallelActionExecutor]`
     - `parallel_config: Dict[str, Any]`
   - 修改方法：
     - `__init__()`：初始化并行执行器
     - `expand()`：改为并行实现
     - `__del__()`或`cleanup()`：确保线程池正确关闭

3. **修改类**：`BOInterface`（在bo_interface.py中）
   - 添加属性：
     - `max_retries: int`（默认5）
   - 修改方法：
     - `generate_heuristic_by_action()`：集成重试逻辑

4. **修改类**：`HeuristicNode`（在bo_local.py中）
   - 添加属性：
     - `generation_status: str`（"pending", "generating", "success", "failed"）
     - `generation_attempts: int`（尝试次数）

[Dependencies]
使用Python标准库的并发模块，无需额外依赖。

依赖修改：
1. **核心依赖**：`concurrent.futures`（Python 3.2+标准库）
   - 用途：线程池管理和并行任务执行
   - 版本：Python内置，无需安装

2. **可选依赖**：无新增外部依赖
   - 保持现有依赖不变：`botorch`, `gpytorch`, `scikit-learn`, `openai`等

3. **兼容性**：
   - 确保代码在Python 3.8+上运行正常
   - 跨平台支持：macOS, Linux, Windows
   - 线程安全：避免使用平台特定的线程特性

[Testing]
添加单元测试和集成测试验证并行执行正确性。

测试策略：
1. **单元测试**：`tests/test_parallel_expand.py`
   - 测试`ParallelActionExecutor`类的各个方法
   - 测试重试逻辑（模拟失败场景）
   - 测试线程安全性

2. **集成测试**：修改现有测试
   - 更新`tests/test_bo_local.py`（如果存在）
   - 验证`expand()`方法返回正确数量的子节点
   - 验证特征向量在评估前已生成

3. **性能测试**：添加基准测试
   - 比较串行vs并行执行时间
   - 验证并行执行确实更快
   - 测试不同worker数量的性能影响

4. **错误处理测试**：
   - 测试API失败时的重试行为
   - 测试超时处理
   - 测试内存泄漏（线程池正确关闭）

5. **跨平台测试**：
   - 确保代码在主要操作系统上行为一致
   - 测试线程池在不同平台上的表现

[Implementation Order]
按逻辑顺序实施修改，确保每一步都可测试和回滚。

实施步骤：
1. **步骤1**：创建`ParallelActionExecutor`类框架
   - 创建`source/parallel_executor.py`文件
   - 实现基本结构和线程池管理
   - 添加单元测试框架

2. **步骤2**：实现带重试的action生成
   - 修改`BOInterface.generate_heuristic_by_action()`添加重试
   - 实现`_generate_with_retry()`方法
   - 测试重试逻辑

3. **步骤3**：集成并行执行到`BayesianOptimizer_Local`
   - 修改`__init__()`初始化并行执行器
   - 创建`_generate_single_action()`辅助方法
   - 实现`_process_generation_results()`方法

4. **步骤4**：重构`expand()`方法
   - 将串行循环改为并行调用
   - 确保所有feature vector在评估前生成
   - 保持现有接口不变

5. **步骤5**：添加同步机制
   - 确保所有线程在返回前完成
   - 添加超时处理
   - 实现优雅的错误处理

6. **步骤6**：全面测试
   - 运行所有现有测试确保无回归
   - 执行性能对比测试
   - 验证跨平台兼容性

7. **步骤7**：文档和清理
   - 更新代码注释和文档
   - 确保线程池正确关闭
   - 优化配置参数