# Phoenix 最終球員資料摘要

生成日期：2026-10-26

## 最終統計

- 球隊容器：574隊
- 有球員資料：436/574隊
- 球員總數：9328人
- 無可核實免費名冊來源：138隊

## 來源分佈

- ESPN API：5423人
- Wikipedia（第一輪及Search API）：3905人
- 其他／未標示：0人

## 出場數政策

- Wikipedia球員的`appearances_25_26=0`代表來源沒有提供出場統計，不代表球員實際出場為0。
- `predict_match.py`遇到`None`或0出場數時，跳過出場數項目，只使用已核實的位置權重，不以0分懲罰球員。
- 沒有球員來源的138隊不會被虛構填充；預測主流程使用436隊，其他隊使用聯賽平均強度fallback。

## 138隊無免費源清單

1. Buyuksehyr（土超）
2. Brondby（丹超）
3. Horsens（丹超）
4. Lyngby（丹超）
5. Silkeborg（丹超）
6. Viborg（丹超）
7. AEK（希超）
8. Aris（希超）
9. Lamia（希超）
10. Blackburn（英冠）
11. Coventry（英冠）
12. Birmingham（英冠）
13. Huddersfield（英冠）
14. Derby（英冠）
15. Bolton（英甲）
16. Cambridge（英甲）
17. Wycombe（英甲）
18. Charlton（英甲）
19. Burton（英甲）
20. Lincoln（英甲）
21. Cheltenham（英甲）
22. Wigan（英甲）
23. Bristol Rvs（英甲）
24. Barnsley（英甲）
25. Exeter（英甲）
26. Peterboro（英甲）
27. Ipswich（英甲）
28. Rotherham（英甲）
29. Accrington（英甲）
30. Morecambe（英甲）
31. Plymouth（英甲）
32. Sheffield Weds（英甲）
33. Derby（英甲）
34. Blackpool（英甲）
35. Carlisle（英甲）
36. Colchester（英甲）
37. Forest Green（英甲）
38. Sutton（英甲）
39. Harrogate（英甲）
40. Rochdale（英甲）
41. Hartlepool（英甲）
42. Mansfield（英甲）
43. Northampton（英甲）
44. Newport County（英甲）
45. Salford（英甲）
46. Swindon（英甲）
47. Stevenage（英甲）
48. Barrow（英甲）
49. Tranmere（英甲）
50. Walsall（英甲）
51. Gillingham（英甲）
52. Doncaster（英甲）
53. Grimsby（英甲）
54. Crewe（英甲）
55. Stockport（英甲）
56. Nurnberg（德乙）
57. Karlsruhe（德乙）
58. Paderborn（德乙）
59. Hannover（德乙）
60. Hamburg（德乙）
61. Darmstadt（德乙）
62. Regensburg（德乙）
63. Magdeburg（德乙）
64. Heidenheim（德乙）
65. Sandhausen（德乙）
66. Hertha（德乙）
67. Elversberg（德乙）
68. Dresden（德乙）
69. Ingolstadt（德乙）
70. Bielefeld（德乙）
71. Osnabruck（德乙）
72. Estudiantes L.P.（阿甲）
73. Godoy Cruz（阿甲）
74. Gimnasia L.P.（阿甲）
75. Central Cordoba（阿甲）
76. Atl. Tucuman（阿甲）
77. Colon Santa FE（阿甲）
78. Arsenal Sarandi（阿甲）
79. New York City（美職MLS）
80. Orlando City（美職MLS）
81. Atlanta Utd（美職MLS）
82. Chicago Fire（美職MLS）
83. Charlotte（美職MLS）
84. Atl. San Luis（墨西超）
85. Hearts（蘇超）
86. Ross County（蘇超）
87. Perugia（意乙）
88. Cittadella（意乙）
89. Brescia（意乙）
90. Ascoli（意乙）
91. Cosenza（意乙）
92. Benevento（意乙）
93. Cremonese（意乙）
94. Pisa（意乙）
95. Spal（意乙）
96. Bari（意乙）
97. Palermo（意乙）
98. Sudtirol（意乙）
99. Modena（意乙）
100. Catanzaro（意乙）
101. Spezia（意乙）
102. Reggiana（意乙）
103. Huesca（西乙）
104. Zaragoza（西乙）
105. Ibiza（西乙）
106. Amorebieta（西乙）
107. Alcorcon（西乙）
108. Sp Gijon（西乙）
109. Burgos（西乙）
110. Oviedo（西乙）
111. Lugo（西乙）
112. Valladolid（西乙）
113. Mirandes（西乙）
114. Cartagena（西乙）
115. Santander（西乙）
116. Andorra（西乙）
117. Ferrol（西乙）
118. Bastia（法乙）
119. Nimes（法乙）
120. Amiens（法乙）
121. Auxerre（法乙）
122. Caen（法乙）
123. Rodez（法乙）
124. Le Havre（法乙）
125. Ajaccio（法乙）
126. Valenciennes（法乙）
127. Niort（法乙）
128. Dijon（法乙）
129. St Etienne（法乙）
130. Laval（法乙）
131. Bordeaux（法乙）
132. Troyes（法乙）
133. Montrose（蘇冠）
134. Clyde（蘇冠）
135. Dumbarton（蘇冠）
136. Peterhead（蘇冠）
137. Alloa（蘇冠）
138. Queen of Sth（蘇冠）

## 交付檔案

- `final_574_squads_with_sources.json`：封存的574隊主檔。
- `predict_match.py`：位置權重球員戰力模組。
- `shared_squad_remaining_failed.json`：未能安全補入的138隊。
