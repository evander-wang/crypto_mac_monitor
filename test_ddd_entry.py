"""
DDD 架构测试入口点
验证新架构可以正常工作
"""

from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from app.infrastructure.container import InfrastructureContainer


def main():
    """测试 DDD 架构入口"""
    print("=" * 60)
    print("DDD 架构测试入口")
    print("=" * 60)

    # 创建容器
    print("\n1. 创建基础设施容器...")
    container = InfrastructureContainer()
    print("   ✓ 容器创建成功")

    # 获取配置提供者
    print("\n2. 获取配置提供者...")
    config_provider = container.config()
    symbols = config_provider.get_symbols()
    print(f"   ✓ 交易对: {symbols}")

    # 获取数据提供者
    print("\n3. 获取数据提供者...")
    data_provider = container.data_provider()
    print(f"   ✓ 数据提供器: {type(data_provider).__name__}")

    # 获取事件发布者
    print("\n4. 获取事件发布者...")
    event_publisher = container.event_publisher()
    print(f"   ✓ 事件发布器: {type(event_publisher).__name__}")

    # 获取 Application 门面
    print("\n5. 获取 Application 门面...")
    application = container.application()
    print(f"   ✓ Application: {type(application).__name__}")

    # 测试获取价格
    print("\n6. 测试获取价格...")
    for symbol in symbols[:1]:  # 只测试第一个
        price = application.get_current_price(symbol)
        print(f"   ✓ {symbol} 价格: {price}")

    print("\n" + "=" * 60)
    print("DDD 架构测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
