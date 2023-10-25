# make sure wiki and homepage are setup by now

export SHOPPING="http://localhost:7770"
export SHOPPING_ADMIN="http://localhost:7780/admin"
export REDDIT="http://localhost:9999"
export GITLAB="http://localhost:8023"
export MAP="http://ec2-3-131-244-37.us-east-2.compute.amazonaws.com:3000/"
export WIKIPEDIA="http://localhost:8888/wikipedia_en_all_maxi_2022-05/"
export HOMEPAGE="http://localhost:4399"

python scripts/generate_test_data.py

mkdir -p ./.auth
python browser_env/auto_login.py
sleep 30

declare -a arr=($SHOPPING $SHOPPING_ADMIN $REDDIT $GITLAB $MAP $WIKIPEDIA $HOMEPAGE)

## now loop through the above array
for i in "${arr[@]}"
do
  echo "$i"
  content=$(curl -L $i)
  echo $content
done
