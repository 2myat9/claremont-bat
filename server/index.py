from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, firestore

# initialize firebase
cred = credentials.Certificate("./claremontbat-firebase-adminsdk.json")
firebase_admin.initialize_app(cred)

# create firestore client
db = firestore.client()

# initialize flask app
app = Flask(__name__)


def handleException(e):
    print("An error occurred:", str(e))
    return jsonify({"error": str(e)}), 500


@app.route("/categories")
def getCategories():
    try:
        categoriesGenerator = db.collection("categories").stream()
        categories = []
        for categorySnapshot in categoriesGenerator:
            categories.append(categorySnapshot.to_dict())

        if len(categories) > 0:
            return jsonify({"categories": categories})
        else:
            return jsonify({"error": "Categories not found"}), 404

    except Exception as e:
        return handleException(e)


@app.route("/categories/<category>")
def getProblems(category):
    try:
        problems = []
        categoryGenerator = db.collection("categories").where("name", "==", category).stream()

        categoryDoc = next(categoryGenerator, None)
        if categoryDoc:
            categoryRef = categoryDoc.reference

            problemsGenerator = db.collection("problems").where("categoryRef", "==", categoryRef).stream()
            for problem in problemsGenerator:
                problem_dict = problem.to_dict()
                problem_dict["categoryRef"] = str(problem_dict["categoryRef"])  # to avoid having a ref object in dict
                problems.append(problem_dict)

        if len(problems) > 0:
            return jsonify({"problems": problems})
        else:
            return jsonify({"error": "Problems not found"}), 404
    except Exception as e:
        return handleException(e)


@app.route("/categories/<category>/<problem>", methods=["GET", "POST"])
def getProblem(category, problem):
    if request.method == "GET":
        try:
            problemRef = db.collection("problems").document(problem)
            problemSnapshot = problemRef.get()
            if problemSnapshot.exists:
                problemData = problemSnapshot.to_dict()

                # since categoryRef is DocumentRef and not JSON serializablee,
                # fetch category data and replace with it
                if "categoryRef" in problemData:
                    categoryRef = problemData["categoryRef"]
                    categorySnapshot = categoryRef.get()
                    categoryData = categorySnapshot.to_dict()
                    problemData["categoryRef"] = categoryData

                return jsonify({"problem": problemData})
            else:
                return jsonify({"error": "Problem not found"}), 404
        except Exception as e:
            return handleException(e)
    elif request.method == "POST":
        # TODO: clear global namespace after running
        try:
            userCode = request.json

            globalFunc = {}  # object for storing functions in the global namespace
            testResults = {}  # object that contains information about each test case that was run
            failedCount = 0
            passedCount = 0

            # except block is entered if exec fails to compile user-provided code due to syntax errors
            exec(userCode, globals(), globalFunc)

            if "func" not in globalFunc:
                # this block is entered when user code is valid syntax but the function is not named func
                print("func not found")
                return jsonify({"error": "Make sure you write your solution inside a function named 'func'."})

            # get problem-related tests
            problemRef = db.collection("problems").document(problem)
            problemSnapshot = problemRef.get()

            if problemSnapshot.exists:
                problem = problemSnapshot.to_dict()
                testsMap = problem.get("tests")

                testPairs = testsMap.items()

            # try except this - name taken from db:
            f = globalFunc["func"]
            # run all tests
            # NOTE: in Firestore map type, the key is always a string so it needs to be converted to int
            for input, expectedOutput in testPairs:
                # compute the input from the db stuff
                inp = int(input)
                # we havae f, we have inp -- call "run tests"
                calculatedOutput = f(inp)  # *inp # in sep function

                testResults[f"{input} -> {expectedOutput}"] = [
                    calculatedOutput == expectedOutput,
                    calculatedOutput,
                ]
                if calculatedOutput == expectedOutput:
                    passedCount += 1
                else:
                    failedCount += 1

            # return a dict of test case strings mapped to booleans
            # also return actual output if test fails
            return jsonify(
                {
                    "results": testResults,
                    "failedCount": failedCount,
                    "passedCount": passedCount,
                }
            )
        except Exception as e:
            return handleException(e)


if __name__ == "__main__":
    app.run(debug=True)
