conda activate webarena

sudo docker stop shopping shopping_admin forum gitlab wikipedia
sudo docker rm shopping shopping_admin forum gitlab wikipedia

sudo docker run --rm --name forum -p 9999:80 -d postmill-populated-exposed-withimg
sleep 300
sudo docker run --rm --name shopping -p 7770:80 -d shopping_final_0712
sleep 60
sudo docker run --rm --name shopping_admin -p 7780:80 -d shopping_admin_final_0719
sleep 60
sudo docker run --rm --name gitlab -d -p 8023:8023 gitlab-populated-final-port8023 /opt/gitlab/embedded/bin/runsvdir-start
sleep 60

sudo docker exec shopping /var/www/magento2/bin/magento setup:store-config:set --base-url="http://localhost:7770"
sleep 30
sudo docker exec shopping_admin /var/www/magento2/bin/magento setup:store-config:set --base-url="http://localhost:7780/"
sleep 30

sudo docker exec shopping mysql -u magentouser -pMyPassword magentodb -e  'UPDATE core_config_data SET value="http://localhost:7770/" WHERE path = "web/secure/base_url";'
sleep 30
sudo docker exec shopping /var/www/magento2/bin/magento cache:flush
sleep 30

sudo docker exec shopping_admin mysql -u magentouser -pMyPassword magentodb -e  'UPDATE core_config_data SET value="http://localhost:7780/" WHERE path = "web/secure/base_url";'
sleep 30
sudo docker exec shopping_admin /var/www/magento2/bin/magento cache:flush
sleep 30

echo remember to spin up wiki if not done, setup homepage if not done, and export llm api keys

