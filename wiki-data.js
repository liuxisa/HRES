/**
 * UGC Wiki 数据管理
 * 使用 localStorage 作为临时存储，后续可对接后端API
 */

const WikiData = {
    // 存储键名
    STORAGE_KEY: 'hres_ugc_wiki_entries',
    
    // 初始化数据
    init() {
        if (!localStorage.getItem(this.STORAGE_KEY)) {
            // 初始化示例数据
            const sampleEntries = [
                {
                    id: '1',
                    title: '示例国家',
                    type: 'country',
                    content: `# 示例国家

## 基本信息
这是一个示例国家词条，展示了如何编写国家相关的UGC内容。

## 政体制度
- **政体类型**: 君主制
- **国体风格**: 王国
- **统治者**: 示例玩家

## 历史
这个国家建立于游戏初期，经历了多次重大事件...

## 城镇
- 首都：示例城镇
- 其他城镇：城镇A、城镇B

## 外交关系
- 与XX国家保持友好关系
- 与YY国家存在贸易往来`,
                    creator: '系统',
                    lastEditor: '系统',
                    createdAt: Date.now() - 86400000 * 7,
                    updatedAt: Date.now() - 86400000 * 2,
                    views: 0
                },
                {
                    id: '2',
                    title: '示例城镇',
                    type: 'town',
                    content: `# 示例城镇

## 基本信息
这是一个示例城镇词条。

## 城镇信息
- **等级**: 城
- **人口**: 50+
- **领主**: 示例玩家

## 地理位置
位于XX国家的中心地带...

## 主要建筑
- 城镇中心
- 市场
- 多个产业建筑`,
                    creator: '系统',
                    lastEditor: '系统',
                    createdAt: Date.now() - 86400000 * 5,
                    updatedAt: Date.now() - 86400000 * 1,
                    views: 0
                }
            ];
            localStorage.setItem(this.STORAGE_KEY, JSON.stringify(sampleEntries));
        }
    },

    // 获取所有词条
    getAllEntries() {
        this.init();
        const data = localStorage.getItem(this.STORAGE_KEY);
        return data ? JSON.parse(data) : [];
    },

    // 保存所有词条
    saveAllEntries(entries) {
        localStorage.setItem(this.STORAGE_KEY, JSON.stringify(entries));
    },

    // 获取单个词条
    getEntry(id) {
        const entries = this.getAllEntries();
        return entries.find(entry => entry.id === id);
    },

    // 创建词条
    createEntry(entryData) {
        const entries = this.getAllEntries();
        const newEntry = {
            id: Date.now().toString(),
            title: entryData.title,
            type: entryData.type,
            content: entryData.content,
            creator: entryData.creator || '匿名用户',
            lastEditor: entryData.creator || '匿名用户',
            createdAt: Date.now(),
            updatedAt: Date.now(),
            views: 0
        };
        entries.push(newEntry);
        this.saveAllEntries(entries);
        return newEntry;
    },

    // 更新词条
    updateEntry(id, updateData) {
        const entries = this.getAllEntries();
        const index = entries.findIndex(entry => entry.id === id);
        if (index === -1) return null;

        entries[index] = {
            ...entries[index],
            ...updateData,
            lastEditor: '当前用户', // 实际应该从登录状态获取
            updatedAt: Date.now()
        };
        this.saveAllEntries(entries);
        return entries[index];
    },

    // 删除词条
    deleteEntry(id) {
        const entries = this.getAllEntries();
        const filtered = entries.filter(entry => entry.id !== id);
        this.saveAllEntries(filtered);
        return filtered.length < entries.length;
    },

    // 按分类获取词条
    getEntriesByCategory(category) {
        if (category === 'all') {
            return this.getAllEntries();
        }
        return this.getAllEntries().filter(entry => entry.type === category);
    },

    // 搜索词条
    searchEntries(query) {
        if (!query) return this.getAllEntries();
        const lowerQuery = query.toLowerCase();
        return this.getAllEntries().filter(entry => 
            entry.title.toLowerCase().includes(lowerQuery) ||
            entry.content.toLowerCase().includes(lowerQuery)
        );
    },

    // 增加浏览量
    incrementViews(id) {
        const entries = this.getAllEntries();
        const index = entries.findIndex(entry => entry.id === id);
        if (index !== -1) {
            entries[index].views = (entries[index].views || 0) + 1;
            this.saveAllEntries(entries);
        }
    },

    // 获取热门词条（按浏览量）
    getPopularEntries(limit = 10) {
        const entries = this.getAllEntries();
        return entries
            .sort((a, b) => (b.views || 0) - (a.views || 0))
            .slice(0, limit);
    },

    // 获取最新词条
    getRecentEntries(limit = 10) {
        const entries = this.getAllEntries();
        return entries
            .sort((a, b) => b.updatedAt - a.updatedAt)
            .slice(0, limit);
    }
};

// 创建全局wikiData对象，提供简化的API
const wikiData = {
    getEntries(category = 'all') {
        return WikiData.getEntriesByCategory(category);
    },

    getEntry(id) {
        return WikiData.getEntry(id);
    },

    createEntry(data) {
        return WikiData.createEntry(data);
    },

    updateEntry(id, data) {
        return WikiData.updateEntry(id, data);
    },

    deleteEntry(id) {
        return WikiData.deleteEntry(id);
    },

    searchEntries(query) {
        return WikiData.searchEntries(query);
    },

    getPopularEntries(limit) {
        return WikiData.getPopularEntries(limit);
    },

    getRecentEntries(limit) {
        return WikiData.getRecentEntries(limit);
    }
};

// 初始化
WikiData.init();

/**
 * 后端API对接接口（预留）
 * 当后端API准备好后，可以替换localStorage的实现
 */
const WikiAPI = {
    // 获取所有词条
    async getAllEntries() {
        // TODO: 对接后端API
        // const response = await fetch('/api/wiki/entries');
        // return await response.json();
        return WikiData.getAllEntries();
    },

    // 获取单个词条
    async getEntry(id) {
        // TODO: 对接后端API
        // const response = await fetch(`/api/wiki/entries/${id}`);
        // return await response.json();
        return WikiData.getEntry(id);
    },

    // 创建词条
    async createEntry(entryData) {
        // TODO: 对接后端API
        // const response = await fetch('/api/wiki/entries', {
        //     method: 'POST',
        //     headers: { 'Content-Type': 'application/json' },
        //     body: JSON.stringify(entryData)
        // });
        // return await response.json();
        return WikiData.createEntry(entryData);
    },

    // 更新词条
    async updateEntry(id, updateData) {
        // TODO: 对接后端API
        // const response = await fetch(`/api/wiki/entries/${id}`, {
        //     method: 'PUT',
        //     headers: { 'Content-Type': 'application/json' },
        //     body: JSON.stringify(updateData)
        // });
        // return await response.json();
        return WikiData.updateEntry(id, updateData);
    },

    // 删除词条
    async deleteEntry(id) {
        // TODO: 对接后端API
        // const response = await fetch(`/api/wiki/entries/${id}`, {
        //     method: 'DELETE'
        // });
        // return await response.json();
        return WikiData.deleteEntry(id);
    }
};











